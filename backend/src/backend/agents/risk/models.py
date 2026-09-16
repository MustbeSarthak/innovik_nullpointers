"""Structured, patient-facing risk result models."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    """Conservative severity bands used by every risk agent."""

    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class RiskEvidence(BaseModel):
    """A grounded observation with its source and provenance."""

    source: str
    detail: str
    document_id: str | None = None
    filename: str | None = None
    document_type: str | None = None
    field: str | None = None
    timestamp: str | None = None
    observed_value: float | None = None
    reference_range: str | None = None


class RiskFinding(BaseModel):
    """One risk signal; it is never a diagnosis."""

    model_config = ConfigDict(extra="forbid")

    agent: str
    risk_level: RiskLevel
    score: int = Field(ge=0, le=100)
    finding: str
    evidence: list[RiskEvidence] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reason: str
    affected_vital: str | None = None
    observed_value: float | None = None
    reference_range: str | None = None
    timestamp: str | None = None
    source: str | None = None


class RiskResult(BaseModel):
    """Result emitted by one specialized risk agent."""

    model_config = ConfigDict(extra="forbid")

    agent: str
    risk_level: RiskLevel
    score: int = Field(ge=0, le=100)
    findings: list[RiskFinding] = Field(default_factory=list)
    evidence: list[RiskEvidence] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    reason: str


class RiskAssessment(BaseModel):
    """Aggregated patient-facing risk assessment."""

    model_config = ConfigDict(extra="forbid")

    patient_id: int
    overall_risk: RiskLevel
    score: int = Field(ge=0, le=100)
    findings: list[RiskFinding] = Field(default_factory=list)
    evidence: list[RiskEvidence] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    recommended_action: str
    detected_indicators: list[str] = Field(default_factory=list)
    escalation_required: bool = False
    ai_provider: str = "deterministic"
    disclaimer: str = (
        "This is an AI-generated risk assessment and is not a medical diagnosis. "
        "It does not replace advice from a qualified healthcare professional."
    )


class RiskRequest(BaseModel):
    """Patient request for a current risk evaluation."""

    query: str = Field(
        default="current health risks symptoms medications allergies medical history"
    )
    vitals: list[dict[str, object]] = Field(default_factory=list)
