"""Medical-history risk specialist."""

from backend.agents.risk.common import assessment_evidence, level_for_score, memory_evidence
from backend.agents.risk.models import RiskResult
from backend.agents.risk.state import RiskInput


_HIGH_CONDITIONS = {"heart_related", "kidney_related"}


def evaluate_history(data: RiskInput) -> RiskResult:
    """Evaluate recorded diagnoses/events without inferring new diagnoses."""
    assessment = data.assessment
    findings = []
    evidence = []
    uncertainties = []
    score = 0
    if assessment is None:
        uncertainties.append("No health assessment is available for medical history.")
    else:
        conditions = [item.condition.value for item in assessment.medical_history.conditions]
        known = [value for value in conditions if value != "none"]
        if not known:
            uncertainties.append("No prior medical conditions are recorded.")
        for condition in known:
            detail = next(
                (item.details for item in assessment.medical_history.conditions if item.condition.value == condition),
                None,
            )
            text = condition if not detail else f"{condition}: {detail}"
            evidence.append(assessment_evidence("medical_history.conditions", text))
        score = min(75, len(known) * 10 + sum(20 for item in known if item in _HIGH_CONDITIONS))
        if known:
            findings.append(
                {
                    "agent": "medical_history_risk",
                    "risk_level": level_for_score(score),
                    "score": score,
                    "finding": "Recorded medical conditions may require continued attention.",
                    "evidence": evidence.copy(),
                    "confidence": 0.95,
                    "reason": "This signal is based only on conditions recorded in the health assessment.",
                }
            )
    for excerpt in data.medical_context.excerpts:
        if excerpt.document_type in {"discharge_summary", "report"} or excerpt.text in data.medical_context.historical_events:
            evidence.append(memory_evidence(excerpt))
    return RiskResult(
        agent="medical_history_risk",
        risk_level=level_for_score(score),
        score=score,
        findings=findings,
        evidence=evidence,
        uncertainties=uncertainties,
        reason="Reviewed recorded conditions and relevant historical excerpts only.",
    )
