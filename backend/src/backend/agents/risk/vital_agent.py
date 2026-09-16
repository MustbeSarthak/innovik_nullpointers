"""Vital/monitoring risk specialist with a future-stream interface."""

from backend.agents.risk.common import assessment_evidence, level_for_score
from backend.agents.risk.models import RiskResult
from backend.agents.risk.state import RiskInput
from backend.vitals.reference_ranges import SexProfile, get_reference_ranges


def evaluate_vitals(data: RiskInput) -> RiskResult:
    """Evaluate supplied readings conservatively; never create absent readings."""
    if not data.vitals:
        return RiskResult(
            agent="vital_monitoring_risk", risk_level="low", score=0, findings=[], evidence=[],
            uncertainties=["No vital or monitoring readings were supplied."],
            reason="Continuous monitoring data is not available for this evaluation.",
        )
    profile = SexProfile.male
    if data.assessment and data.assessment.basic_information.gender.value == "female":
        profile = SexProfile.female
    ranges = get_reference_ranges(profile)
    evidence = []
    findings = []
    score = 0
    for reading in data.vitals:
        name = reading.name.lower()
        canonical = "heart_rate" if name == "heart rate" else name
        reference = ranges.get(canonical)
        outside = reference and not reference.low <= reading.value <= reference.high
        detail = f"{reading.name}={reading.value} {reading.unit}"
        if reference:
            detail += f"; demo range={reference.low}-{reference.high} {reference.unit}"
        item_evidence = assessment_evidence("vitals", detail)
        item_evidence = item_evidence.model_copy(update={
            "timestamp": reading.recorded_at,
            "observed_value": reading.value,
            "reference_range": f"{reference.low}-{reference.high} {reference.unit}" if reference else None,
        })
        evidence.append(item_evidence)
        if outside:
            contribution = 80 if canonical == "spo2" and reading.value < reference.low else 60
            score = max(score, contribution)
            findings.append({
                "agent": "vital_monitoring_risk", "risk_level": level_for_score(contribution), "score": contribution,
                "finding": f"{reading.name} is outside the configured demo screening range.",
                "evidence": [item_evidence], "confidence": 0.85,
                "reason": "This is a screening signal, not a diagnosis; the observed value and demo range are shown for context.",
                "affected_vital": reading.name, "observed_value": reading.value,
                "reference_range": f"{reference.low}-{reference.high} {reference.unit}",
                "timestamp": reading.recorded_at, "source": "vital_reading",
            })
    if len(findings) >= 2:
        score = min(100, score + 10)
    return RiskResult(
        agent="vital_monitoring_risk", risk_level=level_for_score(score), score=score,
        findings=findings, evidence=evidence, uncertainties=[],
        reason="Reviewed only the monitoring readings supplied with this request.",
    )
