"""Allergy risk specialist."""

from backend.agents.risk.common import assessment_evidence, level_for_score
from backend.agents.risk.models import RiskResult
from backend.agents.risk.state import RiskInput


def evaluate_allergies(data: RiskInput) -> RiskResult:
    """Report known allergies and avoid assuming undocumented conflicts."""
    allergies = [] if data.assessment is None else data.assessment.allergies.allergies
    medications = [] if data.assessment is None else data.assessment.medications.medications
    evidence = [
        assessment_evidence("allergies", f"{item.allergen}: {item.description or 'description not provided'}")
        for item in allergies
    ]
    uncertainties = []
    if not allergies:
        uncertainties.append("No allergies are recorded; absence of a record does not prove absence of allergy.")
    if allergies and not medications:
        uncertainties.append("No current medications are recorded for a medication/allergy comparison.")
    score = min(60, len(allergies) * 15)
    findings = [] if not allergies else [{
        "agent": "allergy_risk", "risk_level": level_for_score(score), "score": score,
        "finding": "Known allergies should be communicated before medicines or treatments are given.",
        "evidence": evidence.copy(), "confidence": 0.95,
        "reason": "Only allergies explicitly recorded in the patient assessment were considered; no conflict was assumed.",
    }]
    return RiskResult(
        agent="allergy_risk", risk_level=level_for_score(score), score=score,
        findings=findings, evidence=evidence, uncertainties=uncertainties,
        reason="Reviewed explicitly recorded allergies without inferring undocumented allergies or conflicts.",
    )
