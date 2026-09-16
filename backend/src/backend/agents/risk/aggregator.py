"""Deterministic aggregation of specialized risk results."""

from collections.abc import Iterable

from backend.agents.risk.common import level_for_score
from backend.agents.risk.models import RiskAssessment, RiskFinding, RiskEvidence, RiskLevel, RiskResult


def aggregate_risks(patient_id: int, results: Iterable[RiskResult]) -> RiskAssessment:
    """Deduplicate grounded findings and calculate a conservative overall result."""
    results = list(results)
    findings: list[RiskFinding] = []
    evidence: list[RiskEvidence] = []
    uncertainties: list[str] = []
    seen_findings: set[str] = set()
    seen_evidence: set[tuple[str, str, str | None]] = set()
    for result in results:
        uncertainties.extend(result.uncertainties)
        for finding in result.findings:
            key = finding.finding.strip().casefold()
            if key not in seen_findings:
                seen_findings.add(key)
                findings.append(finding)
        for item in result.evidence:
            key = (item.source, item.detail, item.document_id)
            if key not in seen_evidence:
                seen_evidence.add(key)
                evidence.append(item)
    score = max((finding.score for finding in findings), default=0)
    contributing_agents = {finding.agent for finding in findings}
    if len(contributing_agents) >= 2:
        score = min(100, score + 5)
    level = max((finding.risk_level for finding in findings), key=_severity_rank, default=RiskLevel.low)
    if score >= 80:
        level = RiskLevel.critical if any(item.risk_level is RiskLevel.critical for item in findings) else RiskLevel.high
    else:
        level = level_for_score(score)
    if level in {RiskLevel.high, RiskLevel.critical}:
        action = "Seek prompt professional medical advice. If symptoms feel severe, sudden, or life-threatening, contact emergency services now."
    elif level is RiskLevel.moderate:
        action = "Arrange a timely conversation with a healthcare professional and monitor for worsening symptoms."
    else:
        action = "Continue routine care and monitoring. Seek professional advice if symptoms change or worsen."
    return RiskAssessment(
        patient_id=patient_id,
        overall_risk=level,
        score=score,
        findings=findings,
        evidence=evidence,
        uncertainties=_unique(uncertainties),
        recommended_action=action,
        detected_indicators=[finding.finding for finding in findings],
        escalation_required=score >= 70,
    )


def _severity_rank(level: RiskLevel) -> int:
    return {RiskLevel.low: 0, RiskLevel.moderate: 1, RiskLevel.high: 2, RiskLevel.critical: 3}[level]


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output
