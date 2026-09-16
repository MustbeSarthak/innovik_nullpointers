"""Patient identity model.

The patient row is the single source of truth for ``patient_id``; every other
module (survey, and later the Memory/Risk/Monitoring/Response agents) refers to
this primary key instead of creating its own patient record.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:  # pragma: no cover - typing only
    from backend.models.health_assessment import HealthAssessment


class Patient(Base):
    """A registered patient of the healthcare assistant."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column("patient_id", primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assessment: Mapped["HealthAssessment | None"] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Patient id={self.id} email={self.email!r}>"
