"""Current-symptom risk specialist."""

from backend.agents.risk.common import assessment_evidence, level_for_score
from backend.agents.risk.models import RiskResult
from backend.agents.risk.state import RiskInput


def evaluate_symptoms(data: RiskInput) -> RiskResult:
    """Identify symptom risk signals without diagnosing disease."""
    symptoms = [] if data.assessment is None else data.assessment.current_symptoms.symptoms
    findings = []
    evidence = []
    uncertainties = []
    if not symptoms:
        uncertainties.append("No current symptoms are recorded.")
    severe = [item for item in symptoms if item.severity.value == "severe"]
    moderate = [item for item in symptoms if item.severity.value == "moderate"]
    score = min(100, len(severe) * 40 + len(moderate) * 20 + max(0, len(symptoms) - 2) * 10)
    for item in symptoms:
        evidence.append(
            assessment_evidence(
                "current_symptoms",
                f"{item.symptom}; duration={item.duration}; severity={item.severity.value}",
            )
        )
    if symptoms:
        label = "Severe or multiple symptoms are recorded; prompt professional review may be appropriate." if score >= 55 else "Recorded symptoms are a risk signal to monitor and discuss with a healthcare professional."
        findings.append(
            {
                "agent": "symptom_risk",
                "risk_level": level_for_score(score),
                "score": score,
                "finding": label,
                "evidence": evidence.copy(),
                "confidence": 0.9,
                "reason": "Severity, duration, and symptom count were used; no disease diagnosis was made.",
            }
        )
    return RiskResult(
        agent="symptom_risk", risk_level=level_for_score(score), score=score,
        findings=findings, evidence=evidence, uncertainties=uncertainties,
        reason="Reviewed recorded symptom severity, duration, and count without diagnosing.",
    )
