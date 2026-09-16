"""Patient document persistence and ingestion orchestration."""

import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.exceptions import (
    DocumentIngestionError,
    DocumentNotFoundError,
    DocumentTooLargeError,
)
from backend.models.patient_document import DocumentStatus, DocumentType, PatientDocument
from backend.rag.ingest import IngestionResult, delete_document, index_document
from backend.rag.loaders import load_bytes

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def get_document(db: Session, patient_id: int, document_id: int) -> PatientDocument:
    """Return a document owned by ``patient_id`` or raise not-found."""
    document = db.scalar(
        select(PatientDocument).where(
            PatientDocument.id == document_id,
            PatientDocument.patient_id == patient_id,
        )
    )
    if document is None:
        raise DocumentNotFoundError(
            f"document {document_id} was not found for patient {patient_id}"
        )
    return document


def list_documents(db: Session, patient_id: int) -> list[PatientDocument]:
    """Return the patient's documents newest first."""
    return list(
        db.scalars(
            select(PatientDocument)
            .where(PatientDocument.patient_id == patient_id)
            .order_by(PatientDocument.created_at.desc(), PatientDocument.id.desc())
        )
    )


def _storage_path(filename: str) -> Path:
    settings = get_settings()
    safe_name = _SAFE_FILENAME.sub("_", Path(filename).name).strip("._") or "document"
    directory = Path(settings.document_storage_directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{uuid.uuid4().hex}-{safe_name}"


def upload_document(
    db: Session,
    patient_id: int,
    *,
    data: bytes,
    filename: str,
    content_type: str | None,
    title: str,
    document_type: DocumentType,
    description: str | None = None,
) -> PatientDocument:
    """Persist and index a patient document, recording failures in metadata."""
    settings = get_settings()
    max_size = settings.max_document_size_mb * 1024 * 1024
    if len(data) > max_size:
        raise DocumentTooLargeError(
            f"document exceeds the configured {settings.max_document_size_mb} MB limit"
        )
    try:
        loaded = load_bytes(data, filename)
    except DocumentIngestionError:
        raise

    document = PatientDocument(
        patient_id=patient_id,
        title=title.strip(),
        filename=Path(filename).name,
        content_type=content_type,
        document_type=document_type,
        status=DocumentStatus.pending,
        size_bytes=len(data),
        description=description,
    )
    db.add(document)
    db.flush()
    storage_path = _storage_path(filename)
    document.storage_path = str(storage_path)
    storage_path.write_bytes(data)
    try:
        result: IngestionResult = index_document(
            document.id,
            patient_id,
            loaded,
            filename=document.filename,
            document_type=document_type.value,
            created_at=(
                document.created_at.isoformat() if document.created_at is not None else None
            ),
        )
    except Exception as exc:
        document.status = DocumentStatus.failed
        document.failure_reason = str(exc)[:500]
        db.commit()
        raise
    document.status = DocumentStatus.indexed
    document.page_count = result.page_count
    document.chunk_count = result.chunk_count
    db.commit()
    db.refresh(document)
    return document


def remove_document(db: Session, patient_id: int, document_id: int) -> None:
    """Remove relational metadata, vectors, and the stored original."""
    document = get_document(db, patient_id, document_id)
    delete_document(document.id, patient_id)
    if document.storage_path:
        Path(document.storage_path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()
