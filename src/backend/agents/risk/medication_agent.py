"""Medication risk specialist."""

from backend.agents.risk.common import assessment_evidence, level_for_score
from backend.agents.risk.models import RiskResult
from backend.agents.risk.state import RiskInput


def evaluate_medications(data: RiskInput) -> RiskResult:
    """Review medication completeness and polypharmacy signals without inventing interactions."""
    medications = [] if data.assessment is None else data.assessment.medications.medications
    evidence = [
        assessment_evidence("medications", f"{item.name}; dosage={item.dosage}; frequency={item.frequency}")
        for item in medications
    ]
    uncertainties = []
    if not medications:
        uncertainties.append("No current medications are recorded; medication risk cannot be assessed.")
    if medications and len(medications) >= 3:
        score = 30
        finding = "Multiple current medications are recorded; a medication review may be useful."
    elif medications:
        score = 5
        finding = "Current medications are recorded; no interaction assessment was performed."
    else:
        score = 0
        finding = "No medication-related risk signal was identified from the available data."
    findings = [] if not medications else [{
        "agent": "medication_risk", "risk_level": level_for_score(score), "score": score,
        "finding": finding, "evidence": evidence.copy(), "confidence": 0.9,
        "reason": "Medication names, dosage, frequency, and count were reviewed. Interaction information is unavailable.",
    }]
    return RiskResult(
        agent="medication_risk", risk_level=level_for_score(score), score=score,
        findings=findings, evidence=evidence, uncertainties=uncertainties,
        reason="Reviewed recorded medication details; no drug interaction was inferred.",
    )
