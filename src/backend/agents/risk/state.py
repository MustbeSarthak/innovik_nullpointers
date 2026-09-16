"""Typed input/state contracts for the risk graph."""

from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from backend.memory.schemas import MedicalContext
from backend.schemas.assessment import HealthAssessmentRead


class VitalReading(BaseModel):
    """Optional future monitoring input; absent values stay absent."""

    name: str = Field(min_length=1, max_length=80)
    value: float
    unit: str = Field(min_length=1, max_length=30)
    recorded_at: str | None = None


class RiskInput(BaseModel):
    """Grounded data supplied to every specialized risk agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    patient_id: int = Field(gt=0)
    assessment: HealthAssessmentRead | None = None
    medical_context: MedicalContext
    vitals: list[VitalReading] = Field(default_factory=list)
    recent_vitals: list[dict[str, Any]] = Field(default_factory=list)


class RiskGraphState(TypedDict, total=False):
    """State passed through the LangGraph risk workflow."""

    patient_id: int
    query: str
    assessment: HealthAssessmentRead | None
    medical_context: MedicalContext
    vitals: list[VitalReading]
    recent_vitals: list[dict[str, Any]]
    risk_input: RiskInput
    specialist_results: list[Any]
    final_assessment: Any
    response: Any
