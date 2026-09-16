"""Focused Module 5 tests for specialists, aggregation, graph, and API."""

from datetime import datetime

import pytest

from backend.agents.risk.aggregator import aggregate_risks
from backend.agents.risk.allergy_agent import evaluate_allergies
from backend.agents.risk.condition_agent import evaluate_conditions
from backend.agents.risk.history_agent import evaluate_history
from backend.agents.risk.medication_agent import evaluate_medications
from backend.agents.risk.models import RiskEvidence, RiskFinding, RiskLevel, RiskResult
from backend.agents.risk.orchestrator import RiskEvaluationAgent, build_risk_graph
from backend.agents.risk.state import RiskInput, VitalReading
from backend.agents.risk.symptom_agent import evaluate_symptoms
from backend.agents.risk.vital_agent import evaluate_vitals
from backend.core.config import get_settings
from backend.memory.schemas import MedicalContext, MedicalContextSource
from backend.rag.ingest import reset_vector_store
from backend.schemas.assessment import CurrentSymptomsSection, HealthAssessmentRead
from backend.services.assessment_service import create_assessment, to_read_model


class StubMemoryAgent:
    def __init__(self, context: MedicalContext) -> None:
        self.context = context
        self.patient_ids: list[int] = []

    def retrieve_context(self, patient_id: int, query: str) -> MedicalContext:
        self.patient_ids.append(patient_id)
        return self.context.model_copy(update={"patient_id": patient_id, "query": query})


def _assessment() -> HealthAssessmentRead:
    return HealthAssessmentRead.model_validate(
        {
            "id": 1,
            "patient_id": 7,
            "status": "submitted",
            "basic_information": {
                "age": 52,
                "gender": "female",
                "height_cm": 165,
                "weight_kg": 90,
                "bmi": 33.06,
                "bmi_category": "obese",
            },
            "medical_history": {
                "conditions": [
                    {"condition": "diabetes", "details": None},
                    {"condition": "heart_related", "details": None},
                ]
            },
            "current_symptoms": {
                "symptoms": [
                    {
                        "symptom": "chest discomfort",
                        "duration": "2 hours",
                        "severity": "severe",
                        "notes": "new",
                    },
                    {
                        "symptom": "shortness of breath",
                        "duration": "2 hours",
                        "severity": "moderate",
                        "notes": None,
                    },
                ]
            },
            "medications": {
                "medications": [
                    {"name": "Metformin", "dosage": "500 mg", "frequency": "daily"},
                    {"name": "Medicine B", "dosage": "10 mg", "frequency": "daily"},
                    {"name": "Medicine C", "dosage": "5 mg", "frequency": "daily"},
                ]
            },
            "allergies": {"allergies": [{"allergen": "Penicillin", "description": "rash"}]},
            "additional_information": "Recent hospital follow-up.",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )


def _input(context: MedicalContext | None = None) -> RiskInput:
    return RiskInput(
        patient_id=7,
        assessment=_assessment(),
        medical_context=context or MedicalContext(patient_id=7, query="risk", available=False, status="unavailable"),
    )


def test_each_specialized_agent_returns_grounded_structured_results() -> None:
    data = _input()
    results = [
        evaluate_history(data),
        evaluate_symptoms(data),
        evaluate_medications(data),
        evaluate_allergies(data),
        evaluate_conditions(data),
        evaluate_vitals(data),
    ]

    assert [result.agent for result in results] == [
        "medical_history_risk",
        "symptom_risk",
        "medication_risk",
        "allergy_risk",
        "condition_risk",
        "vital_monitoring_risk",
    ]
    assert results[1].risk_level in {RiskLevel.high, RiskLevel.critical}
    assert results[1].evidence[0].field == "current_symptoms"
    assert "interaction" in results[2].reason.lower()
    assert results[5].uncertainties == ["No vital or monitoring readings were supplied."]


def test_vital_agent_uses_supplied_values_only() -> None:
    data = _input()
    data.vitals = [VitalReading(name="SpO2", value=89, unit="%")]

    result = evaluate_vitals(data)

    assert result.risk_level is RiskLevel.critical
    assert "SpO2=89" in result.evidence[0].detail
    assert "heart rate" not in result.evidence[0].detail.lower()


def test_moderate_symptom_signal_is_not_escalated_to_diagnosis() -> None:
    assessment = _assessment().model_copy(
        update={
            "current_symptoms": CurrentSymptomsSection.model_validate(
                {
                    "symptoms": [
                        {
                            "symptom": "fatigue",
                            "duration": "2 days",
                            "severity": "moderate",
                            "notes": None,
                        },
                        {
                            "symptom": "nausea",
                            "duration": "1 day",
                            "severity": "moderate",
                            "notes": None,
                        },
                    ]
                }
            )
        }
    )
    result = evaluate_symptoms(_input().model_copy(update={"assessment": assessment}))

    assert result.risk_level is RiskLevel.moderate
    assert result.score == 40
    assert "without diagnosing" in result.reason.lower()


def test_empty_data_is_explicitly_uncertain_not_hallucinated() -> None:
    data = RiskInput(
        patient_id=9,
        assessment=None,
        medical_context=MedicalContext(patient_id=9, query="risk", available=False, status="unavailable"),
    )

    results = [evaluate_history(data), evaluate_symptoms(data), evaluate_medications(data), evaluate_allergies(data), evaluate_conditions(data), evaluate_vitals(data)]
    aggregate = aggregate_risks(9, results)

    assert aggregate.overall_risk is RiskLevel.low
    assert aggregate.score == 0
    assert aggregate.findings == []
    assert aggregate.uncertainties
    assert all("diagnos" not in item.finding.lower() for item in aggregate.findings)


def test_aggregator_deduplicates_findings_and_preserves_provenance() -> None:
    evidence = RiskEvidence(source="health_assessment", field="current_symptoms", detail="headache")
    finding = RiskFinding(
        agent="symptom_risk",
        risk_level=RiskLevel.moderate,
        score=40,
        finding="Monitor recorded symptom.",
        evidence=[evidence],
        confidence=0.9,
        reason="Recorded symptom only.",
    )
    result = RiskResult(
        agent="symptom_risk",
        risk_level=RiskLevel.moderate,
        score=40,
        findings=[finding, finding],
        evidence=[evidence, evidence],
        uncertainties=["Missing vitals", "Missing vitals"],
        reason="test",
    )

    aggregate = aggregate_risks(7, [result])

    assert len(aggregate.findings) == 1
    assert len(aggregate.evidence) == 1
    assert aggregate.uncertainties == ["Missing vitals"]
    assert aggregate.findings[0].evidence[0].field == "current_symptoms"


def test_langgraph_executes_and_keeps_patient_id() -> None:
    context = MedicalContext(
        patient_id=7,
        query="risk",
        available=True,
        status="available",
        excerpts=[
            MedicalContextSource(
                text="Prior discharge summary noted follow-up.",
                document_id="doc-1",
                filename="discharge.txt",
                document_type="discharge_summary",
            )
        ],
    )
    memory = StubMemoryAgent(context)
    result = RiskEvaluationAgent(memory).evaluate(
        7, assessment=_assessment(), query="current risk"
    )

    assert result.patient_id == 7
    assert memory.patient_ids == [7]
    assert result.evidence
    assert result.disclaimer.startswith("This is an AI-generated")


def test_patient_scoped_api_evaluation(client, patient, survey_payload, monkeypatch) -> None:
    settings = get_settings()
    settings.embedding_provider = "hashing"
    settings.chroma_mode = "ephemeral"
    reset_vector_store()
    headers = patient["headers"]
    response = client.post("/api/v1/assessments", json=survey_payload, headers=headers)
    assert response.status_code == 201

    response = client.post(
        "/api/v1/risk/evaluate",
        json={"query": "current symptoms and medications"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["patient_id"] == patient["patient_id"]
    assert body["disclaimer"]
    assert all(item["agent"] != "diagnosis" for item in body["findings"])
    reset_vector_store()
