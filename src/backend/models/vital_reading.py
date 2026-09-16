"""Persistent composite vital readings — Module 6."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.patient import Patient


class VitalReading(Base):
    """One complete monitoring sample owned by exactly one patient."""

    __tablename__ = "vital_readings"
    __table_args__ = (
        Index("ix_vital_patient_timestamp", "patient_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column("reading_id", primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    heart_rate: Mapped[float] = mapped_column(Float, nullable=False)
    systolic_bp: Mapped[float] = mapped_column(Float, nullable=False)
    diastolic_bp: Mapped[float] = mapped_column(Float, nullable=False)
    spo2: Mapped[float] = mapped_column(Float, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    glucose: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    simulator_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    simulator_profile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    simulator_scenario: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    patient: Mapped["Patient"] = relationship()