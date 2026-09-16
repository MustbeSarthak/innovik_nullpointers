"""Focused Module 6 tests for monitoring, risk actions, and escalation."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend.alerts.providers import Hospital, MockHospitalProvider, MockSmsProvider
from backend.alerts.service import AlertService
from backend.agents.risk.models import RiskAssessment, RiskLevel
from backend.agents.risk.orchestrator import RiskEvaluationAgent
from backend.agents.risk.state import VitalReading as RiskVitalReading
from backend.core.config import get_settings
from backend.models.alert import AlertStatus
from backend.services.vital_service import history_readings, latest_reading, store_reading
from backend.models.risk_assessment import PatientRiskAssessment
from backend.memory.schemas import MedicalContext
from backend.vitals.reference_ranges import SexProfile, SimulationScenario, SimulationState, get_reference_ranges
from backend.vitals.schemas import VitalReadingCreate, VitalSource
from backend.vitals.simulator import VitalSimulator, generate_demo_reading


def _payload(**overrides) -> VitalReadingCreate:
    values = {
        "heart_rate": 72,
        "systolic_bp": 120,
        "diastolic_bp": 75,
        "spo2": 98,
        "temperature": 36.8,
        "glucose": 95,
        "source": VitalSource.simulator,
        "simulator_state": SimulationState.normal,
        "simulator_profile": SexProfile.female,
    }
    values.update(overrides)
    return VitalReadingCreate.model_validate(values)


def _risk(patient_id: int, score: int) -> RiskAssessment:
    level = RiskLevel.critical if score >= 80 else RiskLevel.high if score >= 70 else RiskLevel.moderate if score >= 50 else RiskLevel.low
    return RiskAssessment(
        patient_id=patient_id,
        overall_risk=level,
        score=score,
        findings=[],
        evidence=[],
        uncertainties=[],
        recommended_action="Monitor and seek appropriate professional care.",
    )


def test_reference_ranges_cover_both_profiles_and_all_vitals() -> None:
    expected = {"heart_rate", "systolic_bp", "diastolic_bp", "spo2", "temperature", "glucose"}
    for profile in (SexProfile.male, SexProfile.female):
        ranges = get_reference_ranges(profile)
        assert set(ranges) == expected
        assert all(item.low < item.high for item in ranges.values())


def test_simulator_generates_marked_valid_state_readings() -> None:
    for state in SimulationState:
        reading = generate_demo_reading(SexProfile.male, state, step=3)
        assert reading.source is VitalSource.simulator
        assert reading.simulator_state is state
        assert reading.simulator_profile is SexProfile.male
        assert reading.heart_rate > 0 and reading.spo2 > 0


def test_simulator_scenarios_show_deterioration_and_recovery() -> None:
    start = generate_demo_reading(SexProfile.male, SimulationState.normal, 0, SimulationScenario.gradual_deterioration)
    worse = generate_demo_reading(SexProfile.male, SimulationState.critical, 10, SimulationScenario.gradual_deterioration)
    recovering = generate_demo_reading(SexProfile.male, SimulationState.critical, 10, SimulationScenario.recovery)
    assert worse.heart_rate > start.heart_rate
    assert worse.spo2 < start.spo2
    assert recovering.heart_rate < worse.heart_rate
    assert recovering.spo2 > worse.spo2


def test_acute_event_changes_values_sharply() -> None:
    before = generate_demo_reading(SexProfile.female, SimulationState.normal, 0, SimulationScenario.acute_event)
    after = generate_demo_reading(SexProfile.female, SimulationState.normal, 1, SimulationScenario.acute_event)
    assert after.heart_rate > before.heart_rate
    assert after.spo2 < before.spo2
    assert after.systolic_bp < before.systolic_bp


def test_simulator_controls_are_per_patient() -> None:
    async def scenario() -> None:
        simulator = VitalSimulator()
        await simulator.start(1, SexProfile.male, SimulationState.normal, 60, lambda: None)
        await simulator.start(2, SexProfile.female, SimulationState.medium, 60, lambda: None)
        simulator.pause(1)
        assert simulator.status(1).paused is True
        assert simulator.status(2).paused is False
        simulator.resume(1)
        simulator.set_state(2, SimulationState.critical)
        assert simulator.status(1).state is SimulationState.normal
        assert simulator.status(2).state is SimulationState.critical
        await simulator.stop(1)
        await simulator.stop(2)

    asyncio.run(scenario())


def test_vital_persistence_history_latest_and_patient_isolation(db, db_patient) -> None:
    first = store_reading(db, db_patient.id, _payload(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    second_patient = type(db_patient)(full_name="Other", email="other@example.com", hashed_password="x")
    db.add(second_patient)
    db.commit()
    store_reading(db, second_patient.id, _payload(timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc)))

    assert latest_reading(db, db_patient.id).id == first.id
    history = history_readings(db, db_patient.id, limit=1)
    assert history.total == 1 and history.items[0].patient_id == db_patient.id


def test_risk_decision_is_persisted_with_provider_provenance(db, db_patient) -> None:
    from backend.services.vital_service import process_reading_risk

    class DeterministicAgent:
        def evaluate(self, *args, **kwargs):
            return _risk(db_patient.id, 75)

    reading = store_reading(db, db_patient.id, _payload())
    process_reading_risk(db, reading, risk_agent=DeterministicAgent())
    saved = db.query(PatientRiskAssessment).filter_by(patient_id=db_patient.id).one()
    assert saved.risk_score == 75
    assert saved.escalation_required is True
    assert saved.source == "SIMULATED"


def test_acno_unavailable_or_malformed_output_keeps_deterministic_safety() -> None:
    class EmptyMemory:
        def retrieve_context(self, patient_id, query):
            return MedicalContext(patient_id=patient_id, query=query, available=False, status="unavailable")

    class BrokenAcno:
        def analyze(self, context):
            raise ValueError("malformed provider response")

    result = RiskEvaluationAgent(EmptyMemory(), BrokenAcno()).evaluate(
        7,
        assessment=None,
        query="acute monitoring",
        vitals=[
            RiskVitalReading(name="spo2", value=86, unit="%"),
            RiskVitalReading(name="heart_rate", value=135, unit="bpm"),
        ],
    )
    assert result.score >= 70
    assert result.ai_provider == "deterministic"
    assert result.escalation_required is True


def test_alert_thresholds_cooldown_sms_ack_and_hospital_escalation(db, db_patient, monkeypatch) -> None:
    settings = get_settings()
    settings.alert_ack_timeout_seconds = 300
    sms = MockSmsProvider()
    hospitals = MockHospitalProvider([
        Hospital("Low Rated", 3.9, 1.0),
        Hospital("Near General", 4.5, 2.0, "Main St", "555"),
        Hospital("Far Medical", 4.8, 8.0),
    ])
    service = AlertService(sms_provider=sms, hospital_provider=hospitals)
    reading = store_reading(db, db_patient.id, _payload())

    assert service.process_reading(db, reading, _risk(db_patient.id, 40)) is None
    special = service.process_reading(db, reading, _risk(db_patient.id, 55))
    assert special.status is AlertStatus.SPECIAL_ATTENTION
    assert service.process_reading(db, reading, _risk(db_patient.id, 60)).id == special.id

    settings.caretaker_phone_number = "+15550001"
    high = service.process_reading(db, reading, _risk(db_patient.id, 85))
    assert high.id != special.id
    assert high.status is AlertStatus.WAITING_FOR_ACK
    assert len(sms.messages) == 1
    assert service.acknowledge(db, db_patient.id, high.id).status is AlertStatus.ACKNOWLEDGED
    assert service.acknowledge(db, db_patient.id, high.id).status is AlertStatus.ACKNOWLEDGED

    expired = service.process_reading(db, reading, _risk(db_patient.id, 90))
    expired.sms_sent_at = datetime.now(timezone.utc) - timedelta(seconds=301)
    db.commit()
    result = service.check_timeouts(db)
    assert result and result[0].status is AlertStatus.HOSPITAL_SEARCH_TRIGGERED
    assert "Near General" in result[0].hospital_result
    assert "Low Rated" not in result[0].hospital_result


def test_vitals_api_is_patient_scoped(client, patient, patient_factory) -> None:
    payload = _payload().model_dump(mode="json")
    response = client.post("/api/v1/vitals", json=payload, headers=patient["headers"])
    assert response.status_code == 201, response.text
    assert response.json()["patient_id"] == patient["patient_id"]
    other = patient_factory()
    response = client.get("/api/v1/vitals/history", headers=other["headers"])
    assert response.status_code == 200
    assert response.json()["total"] == 0
