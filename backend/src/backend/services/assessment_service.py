"""Health assessment (survey) operations.

The service owns every read/write of the survey tables and always works with the
``patient_id`` of an existing patient, so no duplicate patient record can be
created.  It stays free of FastAPI imports so the MCP tools can reuse it.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.exceptions import (
    AssessmentAlreadyExistsError,
    AssessmentNotFoundError,
)
from backend.models.enums import AssessmentStatus
from backend.models.health_assessment import (
    Allergy,
    CurrentSymptoms,
    HealthAssessment,
    Medication,
    MedicalCondition,
)
from backend.schemas.assessment import (
    AllergiesSection,
    BasicInformation,
    BasicInformationRead,
    CurrentSymptomsSection,
    HealthAssessmentCreate,
    HealthAssessmentRead,
    HealthAssessmentUpdate,
    MedicalHistorySection,
    MedicationsSection,
)


# --------------------------------------------------------------------------
# Derived values
# --------------------------------------------------------------------------
def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """Return the body-mass index for ``height_cm`` and ``weight_kg``.

    Raises:
        ValueError: when height is not a positive number.
    """
    if height_cm <= 0:
        raise ValueError("height_cm must be greater than zero")
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 2)


def bmi_category(bmi: float) -> str:
    """Return the WHO weight category for ``bmi``."""
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal"
    if bmi < 30:
        return "overweight"
    return "obese"


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------
def get_assessment(db: Session, patient_id: int) -> HealthAssessment | None:
    """Return the assessment of ``patient_id`` or ``None`` when not submitted."""
    return db.scalar(
        select(HealthAssessment).where(HealthAssessment.patient_id == patient_id)
    )


def require_assessment(db: Session, patient_id: int) -> HealthAssessment:
    """Return the assessment of ``patient_id``.

    Raises:
        AssessmentNotFoundError: when the patient has not submitted one yet.
    """
    assessment = get_assessment(db, patient_id)
    if assessment is None:
        raise AssessmentNotFoundError(
            f"patient {patient_id} has not submitted a health assessment yet"
        )
    return assessment


# --------------------------------------------------------------------------
# Section writers
# --------------------------------------------------------------------------
def _set_basic_information(
    assessment: HealthAssessment, basic: BasicInformation
) -> None:
    """Copy the Basic Information section onto the assessment row."""
    assessment.age = basic.age
    assessment.gender = basic.gender
    assessment.height_cm = basic.height_cm
    assessment.weight_kg = basic.weight_kg
    assessment.bmi = calculate_bmi(basic.height_cm, basic.weight_kg)


def _replace_conditions(
    assessment: HealthAssessment, section: MedicalHistorySection
) -> None:
    """Replace the stored medical history with ``section``."""
    assessment.medical_history = [
        MedicalCondition(condition=item.condition, details=item.details)
        for item in section.conditions
    ]


def _replace_symptoms(
    assessment: HealthAssessment, section: CurrentSymptomsSection
) -> None:
    """Replace the stored symptoms with ``section``."""
    assessment.current_symptoms = [
        CurrentSymptoms(
            symptom=item.symptom,
            duration=item.duration,
            severity=item.severity,
            notes=item.notes,
        )
        for item in section.symptoms
    ]


def _replace_medications(
    assessment: HealthAssessment, section: MedicationsSection
) -> None:
    """Replace the stored medications with ``section``."""
    assessment.medications = [
        Medication(name=item.name, dosage=item.dosage, frequency=item.frequency)
        for item in section.medications
    ]


def _replace_allergies(
    assessment: HealthAssessment, section: AllergiesSection
) -> None:
    """Replace the stored allergies with ``section``."""
    assessment.allergies = [
        Allergy(allergen=item.allergen, description=item.description)
        for item in section.allergies
    ]


def _apply_create_payload(
    assessment: HealthAssessment, payload: HealthAssessmentCreate
) -> None:
    """Apply every section of a full ``POST``/``PUT`` payload."""
    _set_basic_information(assessment, payload.basic_information)
    _replace_conditions(assessment, payload.medical_history)
    _replace_symptoms(assessment, payload.current_symptoms)
    _replace_medications(assessment, payload.medications)
    _replace_allergies(assessment, payload.allergies)
    assessment.additional_information = payload.additional_information


# --------------------------------------------------------------------------
# Writes
# --------------------------------------------------------------------------
def create_assessment(
    db: Session, patient_id: int, payload: HealthAssessmentCreate
) -> HealthAssessment:
    """Store the first health assessment of ``patient_id``.

    Raises:
        AssessmentAlreadyExistsError: when the patient already submitted one;
            the caller should use the update endpoint instead.
    """
    if get_assessment(db, patient_id) is not None:
        raise AssessmentAlreadyExistsError(patient_id)

    # ``_apply_create_payload`` fills every required column, so only the owning
    # patient and the lifecycle status are set here.
    assessment = HealthAssessment(
        patient_id=patient_id, status=AssessmentStatus.submitted
    )
    _apply_create_payload(assessment, payload)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def replace_assessment(
    db: Session, patient_id: int, payload: HealthAssessmentCreate
) -> HealthAssessment:
    """Overwrite the assessment of ``patient_id`` with ``payload`` (PUT).

    Sections that are omitted by the client fall back to their defaults, so a PUT
    always represents the complete survey state.

    Raises:
        AssessmentNotFoundError: when the patient has no assessment yet.
    """
    assessment = require_assessment(db, patient_id)
    _apply_create_payload(assessment, payload)
    assessment.status = AssessmentStatus.updated
    db.commit()
    db.refresh(assessment)
    return assessment


def update_assessment(
    db: Session, patient_id: int, payload: HealthAssessmentUpdate
) -> HealthAssessment:
    """Patch the assessment of ``patient_id`` with the provided sections (PATCH).

    Sections absent from the request body keep their stored values; a provided
    section fully replaces the corresponding child rows.

    Raises:
        AssessmentNotFoundError: when the patient has no assessment yet.
    """
    assessment = require_assessment(db, patient_id)

    if payload.basic_information is not None:
        _set_basic_information(assessment, payload.basic_information)
    if payload.medical_history is not None:
        _replace_conditions(assessment, payload.medical_history)
    if payload.current_symptoms is not None:
        _replace_symptoms(assessment, payload.current_symptoms)
    if payload.medications is not None:
        _replace_medications(assessment, payload.medications)
    if payload.allergies is not None:
        _replace_allergies(assessment, payload.allergies)
    if "additional_information" in payload.model_fields_set:
        assessment.additional_information = payload.additional_information

    assessment.status = AssessmentStatus.updated
    db.commit()
    db.refresh(assessment)
    return assessment


def to_read_model(assessment: HealthAssessment) -> HealthAssessmentRead:
    """Convert an ORM assessment into the API response model."""
    return HealthAssessmentRead(
        id=assessment.id,
        patient_id=assessment.patient_id,
        status=AssessmentStatus(assessment.status),
        basic_information=BasicInformationRead(
            age=assessment.age,
            gender=assessment.gender,
            height_cm=assessment.height_cm,
            weight_kg=assessment.weight_kg,
            bmi=assessment.bmi,
            bmi_category=bmi_category(assessment.bmi) if assessment.bmi else None,
        ),
        medical_history=MedicalHistorySection(
            conditions=[
                {"condition": item.condition, "details": item.details}
                for item in assessment.medical_history
            ]
        ),
        current_symptoms=CurrentSymptomsSection(
            symptoms=[
                {
                    "symptom": item.symptom,
                    "duration": item.duration,
                    "severity": item.severity,
                    "notes": item.notes,
                }
                for item in assessment.current_symptoms
            ]
        ),
        medications=MedicationsSection(
            medications=[
                {
                    "name": item.name,
                    "dosage": item.dosage,
                    "frequency": item.frequency,
                }
                for item in assessment.medications
            ]
        ),
        allergies=AllergiesSection(
            allergies=[
                {"allergen": item.allergen, "description": item.description}
                for item in assessment.allergies
            ]
        ),
        additional_information=assessment.additional_information,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
    )