"""Patient document metadata — Module 4.

Design notes
------------
* Only *metadata* is stored relationally; the vectors live in the Chroma
  ``patient_records`` collection (see :mod:`backend.rag.ingest`).  Patient
  identity is never duplicated: the row points at the existing
  ``patients.patient_id``.
* One row per uploaded file, including the ingestion outcome, so the API can
  list what the patient uploaded without touching the vector store.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:  # pragma: no cover - typing only
    from backend.models.patient import Patient


class DocumentType(str, Enum):
    """Kinds of medical documents a patient may upload.

    Every member value is lower_snake_case and identical to its name, matching
    the convention used by :mod:`backend.models.enums`.
    """

    prescription = "prescription"
    discharge_summary = "discharge_summary"
    blood_report = "blood_report"
    ecg_report = "ecg_report"
    report = "report"
    other = "other"


class DocumentStatus(str, Enum):
    """Ingestion lifecycle of an uploaded document."""

    pending = "pending"
    indexed = "indexed"
    failed = "failed"


def _enum_column(enum_type: type, name: str, *, nullable: bool = False):
    """Create a ``VARCHAR + CHECK`` column for ``enum_type``.

    Mirrors the helper used by :mod:`backend.models.health_assessment` so the
    same schema works on SQLite and PostgreSQL without native enum types.
    """
    return mapped_column(
        SAEnum(
            enum_type,
            name=name,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            length=32,
        ),
        nullable=nullable,
    )


class PatientDocument(Base):
    """Metadata of one medical document uploaded by a patient."""

    __tablename__ = "patient_documents"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_document_size_positive"),
        CheckConstraint("chunk_count >= 0", name="ck_document_chunk_count_positive"),
    )

    id: Mapped[int] = mapped_column("document_id", primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Description of the upload ----------------------------------------
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    document_type: Mapped[DocumentType] = _enum_column(
        DocumentType, "document_type_enum"
    )
    status: Mapped[DocumentStatus] = _enum_column(
        DocumentStatus, "document_status_enum"
    )

    # --- Storage / ingestion bookkeeping ----------------------------------
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    patient: Mapped["Patient"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"<PatientDocument id={self.id} patient_id={self.patient_id} "
            f"filename={self.filename!r}>"
        )