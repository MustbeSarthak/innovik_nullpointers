"""Persistence and risk-processing services for patient vital readings."""

from datetime import datetime, timezone
import json

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.vital_reading import VitalReading
from backend.models.risk_assessment import PatientRiskAssessment
from backend.agents.risk.orchestrator import RiskEvaluationAgent
from backend.agents.risk.state import VitalReading as RiskVitalReading
from backend.services.assessment_service import get_assessment, to_read_model
from backend.alerts.service import AlertService
from backend.vitals.schemas import VitalHistoryRead, VitalReadingCreate, VitalReadingRead


def store_reading(db: Session, patient_id: int, payload: VitalReadingCreate) -> VitalReading:
    """Persist one complete patient-owned reading."""
    reading = VitalReading(
        patient_id=patient_id,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
        heart_rate=payload.heart_rate,
        systolic_bp=payload.systolic_bp,
        diastolic_bp=payload.diastolic_bp,
        spo2=payload.spo2,
        temperature=payload.temperature,
        glucose=payload.glucose,
        source=payload.source.value,
        simulator_state=payload.simulator_state.value if payload.simulator_state else None,
        simulator_profile=payload.simulator_profile.value if payload.simulator_profile else None,
        simulator_scenario=payload.simulator_scenario.value if payload.simulator_scenario else None,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def latest_reading(db: Session, patient_id: int) -> VitalReading | None:
    """Return only the authenticated patient's newest reading."""
    return db.scalar(
        select(VitalReading)
        .where(VitalReading.patient_id == patient_id)
        .order_by(desc(VitalReading.timestamp), desc(VitalReading.id))
        .limit(1)
    )


def history_readings(db: Session, patient_id: int, limit: int = 50, offset: int = 0) -> VitalHistoryRead:
    """Return bounded, newest-first history for one patient."""
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    base = select(VitalReading).where(VitalReading.patient_id == patient_id)
    total = len(db.scalars(base).all())
    rows = list(db.scalars(base.order_by(desc(VitalReading.timestamp), desc(VitalReading.id)).offset(offset).limit(limit)))
    return VitalHistoryRead(
        items=[VitalReadingRead.model_validate(item) for item in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


def process_reading_risk(
    db: Session,
    reading: VitalReading,
    *,
    risk_agent: RiskEvaluationAgent | None = None,
    alert_service: AlertService | None = None,
):
    """Run the stored reading through Module 5 and apply Module 6 actions."""
    assessment = get_assessment(db, reading.patient_id)
    context_query = "current vital monitoring risk and patient medical context"
    risk_vitals = [
        RiskVitalReading(name="heart_rate", value=reading.heart_rate, unit="bpm", recorded_at=reading.timestamp.isoformat()),
        RiskVitalReading(name="systolic_bp", value=reading.systolic_bp, unit="mmHg", recorded_at=reading.timestamp.isoformat()),
        RiskVitalReading(name="diastolic_bp", value=reading.diastolic_bp, unit="mmHg", recorded_at=reading.timestamp.isoformat()),
        RiskVitalReading(name="spo2", value=reading.spo2, unit="%", recorded_at=reading.timestamp.isoformat()),
        RiskVitalReading(name="temperature", value=reading.temperature, unit="C", recorded_at=reading.timestamp.isoformat()),
        RiskVitalReading(name="glucose", value=reading.glucose, unit="mg/dL", recorded_at=reading.timestamp.isoformat()),
    ]
    recent_rows = list(
        db.scalars(
            select(VitalReading)
            .where(VitalReading.patient_id == reading.patient_id)
            .order_by(desc(VitalReading.timestamp), desc(VitalReading.id))
            .limit(10)
        )
    )
    recent_vitals = [
        {
            "timestamp": item.timestamp.isoformat(),
            "heart_rate": item.heart_rate,
            "systolic_bp": item.systolic_bp,
            "diastolic_bp": item.diastolic_bp,
            "spo2": item.spo2,
            "temperature": item.temperature,
            "glucose": item.glucose,
        }
        for item in reversed(recent_rows)
    ]
    risk = (risk_agent or RiskEvaluationAgent()).evaluate(
        reading.patient_id,
        assessment=to_read_model(assessment) if assessment else None,
        query=context_query,
        vitals=risk_vitals,
        recent_vitals=recent_vitals,
    )
    persisted = PatientRiskAssessment(
        patient_id=reading.patient_id,
        timestamp=reading.timestamp,
        risk_level=risk.overall_risk.value,
        risk_score=risk.score,
        detected_indicators=json.dumps(risk.detected_indicators),
        escalation_required=risk.escalation_required or risk.score >= 70,
        source=reading.source,
        ai_provider=risk.ai_provider,
    )
    db.add(persisted)
    db.commit()
    alert = (alert_service or AlertService()).process_reading(db, reading, risk)
    return risk, alert
