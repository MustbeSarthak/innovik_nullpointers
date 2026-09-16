"""Known-condition risk specialist."""

from backend.agents.risk.common import assessment_evidence, level_for_score, memory_evidence
from backend.agents.risk.models import RiskResult
from backend.agents.risk.state import RiskInput


def evaluate_conditions(data: RiskInput) -> RiskResult:
    """Connect recorded conditions to recorded symptoms/history, without diagnosis."""
    assessment = data.assessment
    conditions = [] if assessment is None else [item for item in assessment.medical_history.conditions if item.condition.value != "none"]
    evidence = [assessment_evidence("medical_history.conditions", item.condition.value) for item in conditions]
    evidence.extend(memory_evidence(item) for item in data.medical_context.excerpts if item.document_type in {"blood_report", "ecg_report", "discharge_summary"})
    uncertainties = []
    if not conditions:
        uncertainties.append("No active medical conditions are recorded.")
    score = min(80, sum(25 if item.condition.value in {"heart_related", "kidney_related"} else 15 for item in conditions))
    findings = [] if not conditions else [{
        "agent": "condition_risk", "risk_level": level_for_score(score), "score": score,
        "finding": "Recorded conditions may increase the need for monitoring and follow-up.",
        "evidence": evidence.copy(), "confidence": 0.9,
        "reason": "This signal reflects known conditions and retrieved related records only; it is not a diagnosis.",
    }]
    return RiskResult(
        agent="condition_risk", risk_level=level_for_score(score), score=score,
        findings=findings, evidence=evidence, uncertainties=uncertainties,
        reason="Reviewed known conditions and related retrieved records without adding unsupported conditions.",
    )
