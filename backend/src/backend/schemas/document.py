"""Schemas for patient medical-document uploads and metadata."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.patient_document import DocumentStatus, DocumentType


class PatientDocumentRead(BaseModel):
    """Document metadata returned to an authenticated patient."""

    model_config = ConfigDict(from_attributes=True)

    document_id: int = Field(validation_alias="id")
    title: str
    filename: str
    content_type: str | None
    document_type: DocumentType
    status: DocumentStatus
    size_bytes: int
    page_count: int
    chunk_count: int
    description: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class PatientDocumentList(BaseModel):
    """Paginated document metadata response."""

    items: list[PatientDocumentRead]
    total: int
