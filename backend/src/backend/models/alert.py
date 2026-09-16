"""Persistent risk-alert lifecycle — Module 6."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.patient import Patient


class AlertStatus(str, Enum):
    SPECIAL_ATTENTION = "SPECIAL_ATTENTION"
    CREATED = "CREATED"
    SMS_SENT = "SMS_SENT"
    WAITING_FOR_ACK = "WAITING_FOR_ACK"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    NO_RESPONSE = "NO_RESPONSE"
    HOSPITAL_SEARCH_TRIGGERED = "HOSPITAL_SEARCH_TRIGGERED"


class Alert(Base):
    """One deduplicated risk event for one patient."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alert_patient_status", "patient_id", "status"),
    )

    id: Mapped[int] = mapped_column("alert_id", primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(AlertStatus, native_enum=False, validate_strings=True), nullable=False
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sms_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hospital_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped["Patient"] = relationship()