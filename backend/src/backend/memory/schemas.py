"""Typed state and output models for the Memory Agent."""

from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class MedicalContextSource(BaseModel):
    """A retrieved excerpt and provenance metadata."""

    model_config = ConfigDict(extra="allow")

    text: str
    distance: float | None = None
    document_id: str | None = None
    filename: str | None = None
    document_type: str | None = None
    page_count: int | None = None
    chunk_index: int | None = None
    created_at: str | None = None


class MedicalContext(BaseModel):
    """Grounded patient context assembled from indexed records."""

    patient_id: int
    query: str
    available: bool
    status: str
    diagnoses: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    lab_reports: list[str] = Field(default_factory=list)
    treatments: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    historical_events: list[str] = Field(default_factory=list)
    excerpts: list[MedicalContextSource] = Field(default_factory=list)


class MemoryAgentState(TypedDict, total=False):
    """State passed between LangGraph nodes."""

    patient_id: int
    query: str
    records: list[dict[str, Any]]
    organized_records: list[MedicalContextSource]
    context: MedicalContext


class MemoryAgentRequest(BaseModel):
    """Input accepted by :class:`MemoryAgent`."""

    patient_id: int = Field(gt=0)
    query: str = Field(min_length=1)
