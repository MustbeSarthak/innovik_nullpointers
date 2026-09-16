"""Persisted risk decisions produced by the Module 5/6 pipeline."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.patient import Patient


class PatientRiskAssessment(Base):
    """One immutable screening decision tied to one patient and reading cycle."""

    __tablename__ = "risk_assessments"
    __table_args__ = (Index("ix_risk_patient_timestamp", "patient_id", "timestamp"),)

    id: Mapped[int] = mapped_column("risk_assessment_id", primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    detected_indicators: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    escalation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(40), nullable=False, default="deterministic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient: Mapped["Patient"] = relationship()
