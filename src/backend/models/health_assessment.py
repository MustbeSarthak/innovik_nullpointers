"""Health assessment (survey) models — Module 1.

Design notes
------------
* Exactly one assessment row exists per patient (``patient_id`` is unique) so the
  survey can be submitted once and updated afterwards without ever duplicating
  patient data.
* Repeating survey answers (conditions, symptoms, medications, allergies) live in
  their own child tables instead of JSON columns, which keeps the data
  queryable for the Memory/Risk agents that will consume it later.
* Ranges chosen for the "Basic Information" section are enforced both by the
  API schemas and by database ``CHECK`` constraints.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.enums import (
    AssessmentStatus,
    Gender,
    MedicalConditionType,
    SymptomSeverity,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from backend.models.patient import Patient

# Reusable, database-level validation bounds (they mirror the Pydantic schema).
AGE_MIN, AGE_MAX = 0, 120
HEIGHT_MIN_CM, HEIGHT_MAX_CM = 30.0, 250.0
WEIGHT_MIN_KG, WEIGHT_MAX_KG = 2.0, 500.0


def _enum_column(enum_type: type, name: str, *, nullable: bool = False):
    """Create a ``VARCHAR + CHECK`` column for ``enum_type``.

    Native database enums are avoided so the same schema works on SQLite and
    PostgreSQL, and ``validate_strings`` guarantees invalid values are rejected
    before they reach the database.
    """
    return mapped_column(
        Enum(
            enum_type,
            name=name,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            length=32,
        ),
        nullable=nullable,
    )


class HealthAssessment(Base):
    """One survey submission belonging to a :class:`~backend.models.patient.Patient`."""

    __tablename__ = "health_assessments"
    __table_args__ = (
        CheckConstraint(f"age >= {AGE_MIN} AND age <= {AGE_MAX}", name="ck_age_range"),
        CheckConstraint(
            f"height_cm >= {HEIGHT_MIN_CM} AND height_cm <= {HEIGHT_MAX_CM}",
            name="ck_height_range",
        ),
        CheckConstraint(
            f"weight_kg >= {WEIGHT_MIN_KG} AND weight_kg <= {WEIGHT_MAX_KG}",
            name="ck_weight_range",
        ),
        CheckConstraint("bmi IS NULL OR bmi > 0", name="ck_bmi_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # --- Basic information -------------------------------------------------
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[Gender] = _enum_column(Gender, "gender_enum")
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Additional information -------------------------------------------
    additional_information: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(
            AssessmentStatus,
            name="assessment_status_enum",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            length=32,
        ),
        nullable=False,
        default=AssessmentStatus.submitted,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # --- Relationships -----------------------------------------------------
    patient: Mapped["Patient"] = relationship(back_populates="assessment")

    medical_history: Mapped[list["MedicalCondition"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="MedicalCondition.id",
        lazy="selectin",
    )
    current_symptoms: Mapped[list["CurrentSymptoms"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="CurrentSymptoms.id",
        lazy="selectin",
    )
    medications: Mapped[list["Medication"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="Medication.id",
        lazy="selectin",
    )
    allergies: Mapped[list["Allergy"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="Allergy.id",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<HealthAssessment id={self.id} patient_id={self.patient_id}>"


class MedicalCondition(Base):
    """A single entry of the *Medical History* section."""

    __tablename__ = "medical_conditions"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("health_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    condition: Mapped[MedicalConditionType] = _enum_column(
        MedicalConditionType, "medical_condition_enum"
    )
    details: Mapped[str | None] = mapped_column(String(255), nullable=True)

    assessment: Mapped[HealthAssessment] = relationship(
        back_populates="medical_history"
    )


class CurrentSymptoms(Base):
    """A single reported symptom with its duration and severity."""

    __tablename__ = "current_symptoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("health_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symptom: Mapped[str] = mapped_column(String(200), nullable=False)
    duration: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[SymptomSeverity] = _enum_column(
        SymptomSeverity, "symptom_severity_enum"
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    assessment: Mapped[HealthAssessment] = relationship(
        back_populates="current_symptoms"
    )


class Medication(Base):
    """A medication the patient is currently taking."""

    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("health_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)

    assessment: Mapped[HealthAssessment] = relationship(back_populates="medications")


class Allergy(Base):
    """A known allergy together with its description."""

    __tablename__ = "allergies"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("health_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allergen: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    assessment: Mapped[HealthAssessment] = relationship(back_populates="allergies")