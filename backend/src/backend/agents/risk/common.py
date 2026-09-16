"""Shared deterministic scoring helpers for risk specialists."""

from backend.agents.risk.models import RiskEvidence, RiskLevel


def level_for_score(score: int) -> RiskLevel:
    if score >= 80:
        return RiskLevel.critical
    if score >= 55:
        return RiskLevel.high
    if score >= 25:
        return RiskLevel.moderate
    return RiskLevel.low


def assessment_evidence(field: str, detail: str) -> RiskEvidence:
    return RiskEvidence(source="health_assessment", field=field, detail=detail)


def memory_evidence(excerpt) -> RiskEvidence:
    return RiskEvidence(
        source="medical_memory",
        detail=excerpt.text,
        document_id=excerpt.document_id,
        filename=excerpt.filename,
        document_type=excerpt.document_type,
    )
