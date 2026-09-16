"""Authenticated patient medical-document endpoints."""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from backend.api.deps import CurrentPatient, DbSession
from backend.models.patient_document import DocumentType
from backend.schemas.document import PatientDocumentList, PatientDocumentRead
from backend.services.document_service import (
    get_document,
    list_documents,
    remove_document,
    upload_document,
)

router = APIRouter(prefix="/documents", tags=["Patient Documents"])


@router.post(
    "",
    response_model=PatientDocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a medical document",
)
def create_document(
    patient: CurrentPatient,
    db: DbSession,
    file: Annotated[UploadFile, File(description="PDF, text, or Markdown document")],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    document_type: Annotated[DocumentType, Form()] = DocumentType.other,
    description: Annotated[str | None, Form(max_length=2000)] = None,
) -> PatientDocumentRead:
    """Store a document and index its text for the authenticated patient."""
    data = file.file.read()
    document = upload_document(
        db,
        patient.id,
        data=data,
        filename=file.filename or "document",
        content_type=file.content_type,
        title=title,
        document_type=document_type,
        description=description,
    )
    return PatientDocumentRead.model_validate(document)


@router.get("", response_model=PatientDocumentList, summary="List uploaded documents")
def read_documents(patient: CurrentPatient, db: DbSession) -> PatientDocumentList:
    """List documents belonging to the authenticated patient."""
    items = list_documents(db, patient.id)
    return PatientDocumentList(items=items, total=len(items))


@router.get(
    "/{document_id}",
    response_model=PatientDocumentRead,
    summary="Get uploaded document metadata",
)
def read_document(
    document_id: int, patient: CurrentPatient, db: DbSession
) -> PatientDocumentRead:
    """Return metadata only; document contents remain private to ingestion."""
    return PatientDocumentRead.model_validate(get_document(db, patient.id, document_id))


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an uploaded document",
)
def delete_document(document_id: int, patient: CurrentPatient, db: DbSession) -> None:
    """Delete the patient's document and its indexed chunks."""
    remove_document(db, patient.id, document_id)
