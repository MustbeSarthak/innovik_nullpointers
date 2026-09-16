"""Service-layer tests for the health assessment (no HTTP involved)."""

import pytest

from backend.core.exceptions import (
    AssessmentAlreadyExistsError,
    AssessmentNotFoundError,
)
from backend.models.enums import AssessmentStatus, MedicalConditionType, SymptomSeverity
from backend.schemas.assessment import (
    HealthAssessmentCreate,
    HealthAssessmentUpdate,
)
from backend.services.assessment_service import (
    bmi_category,
    calculate_bmi,
    create_assessment,
    get_assessment,
    replace_assessment,
    require_assessment,
    to_read_model,
    update_assessment,
)


def _create_payload(payload: dict) -> HealthAssessmentCreate:
    """Validate a raw dictionary into the create schema."""
    return HealthAssessmentCreate.model_validate(payload)


def _update_payload(payload: dict) -> HealthAssessmentUpdate:
    """Validate a raw dictionary into the update schema."""
    return HealthAssessmentUpdate.model_validate(payload)


# --------------------------------------------------------------------------
# Derived values
# --------------------------------------------------------------------------
def test_calculate_bmi_and_category() -> None:
    """BMI and its WHO category are derived from height and weight."""
    assert calculate_bmi(165.0, 62.0) == 22.77
    assert calculate_bmi(180.0, 60.0) == 18.52
    assert calculate_bmi(160.0, 100.0) == 39.06

    assert bmi_category(17.0) == "underweight"
    assert bmi_category(22.5) == "normal"
    assert bmi_category(27.0) == "overweight"
    assert bmi_category(31.4) == "obese"


def test_calculate_bmi_rejects_non_positive_height() -> None:
    """A non-positive height is a programming error, not a silent zero."""
    with pytest.raises(ValueError):
        calculate_bmi(0.0, 70.0)


# --------------------------------------------------------------------------
# Create
# --------------------------------------------------------------------------
def test_create_assessment_stores_all_sections(db, db_patient, survey_payload) -> None:
    """The service writes the parent row plus every normalised child row."""
    assessment = create_assessment(
        db, db_patient.id, _create_payload(survey_payload)
    )

    assert assessment.id is not None
    assert assessment.patient_id == db_patient.id
    assert assessment.status is AssessmentStatus.submitted
    assert assessment.bmi == 22.77
    assert [item.condition for item in assessment.medical_history] == [
        MedicalConditionType.diabetes,
        MedicalConditionType.other,
    ]
    assert [item.severity for item in assessment.current_symptoms] == [
        SymptomSeverity.moderate,
        SymptomSeverity.mild,
    ]
    assert assessment.medications[0].name == "Metformin"
    assert assessment.allergies[0].allergen == "Penicillin"


def test_create_assessment_twice_raises(db, db_patient, survey_payload) -> None:
    """Only one assessment per patient is allowed."""
    create_assessment(db, db_patient.id, _create_payload(survey_payload))

    with pytest.raises(AssessmentAlreadyExistsError) as excinfo:
        create_assessment(db, db_patient.id, _create_payload(survey_payload))

    assert excinfo.value.patient_id == db_patient.id


def test_create_assessment_with_required_sections_only(
    db, db_patient, minimal_payload
) -> None:
    """Optional sections stay empty for a required-only submission."""
    assessment = create_assessment(db, db_patient.id, _create_payload(minimal_payload))

    assert assessment.current_symptoms == []
    assert assessment.medications == []
    assert assessment.allergies == []
    assert assessment.additional_information is None


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------
def test_get_and_require_assessment(db, db_patient, minimal_payload) -> None:
    """``get_assessment`` returns ``None`` while ``require_assessment`` raises."""
    assert get_assessment(db, db_patient.id) is None
    with pytest.raises(AssessmentNotFoundError):
        require_assessment(db, db_patient.id)

    create_assessment(db, db_patient.id, _create_payload(minimal_payload))

    assert require_assessment(db, db_patient.id).patient_id == db_patient.id


def test_to_read_model_exposes_bmi_category(db, db_patient, survey_payload) -> None:
    """The read model is what the API and the MCP tools serialise."""
    assessment = create_assessment(
        db, db_patient.id, _create_payload(survey_payload)
    )

    model = to_read_model(assessment)

    assert model.patient_id == db_patient.id
    assert model.basic_information.bmi_category == "normal"
    assert model.status is AssessmentStatus.submitted
    assert len(model.current_symptoms.symptoms) == 2


# --------------------------------------------------------------------------
# Update
# --------------------------------------------------------------------------
def test_update_assessment_replaces_only_given_sections(
    db, db_patient, survey_payload
) -> None:
    """PATCH semantics: omitted sections keep their stored values."""
    create_assessment(db, db_patient.id, _create_payload(survey_payload))

    assessment = update_assessment(
        db,
        db_patient.id,
        _update_payload(
            {"medications": {"medications": [{"name": "Ibuprofen", "dosage": "200 mg", "frequency": "as needed"}]}}
        ),
    )

    assert [item.name for item in assessment.medications] == ["Ibuprofen"]
    assert assessment.allergies[0].allergen == "Penicillin"
    assert assessment.status is AssessmentStatus.updated


def test_update_assessment_can_clear_a_section(db, db_patient, survey_payload) -> None:
    """Passing an empty list clears that section."""
    create_assessment(db, db_patient.id, _create_payload(survey_payload))

    assessment = update_assessment(
        db, db_patient.id, _update_payload({"allergies": {"allergies": []}})
    )

    assert assessment.allergies == []


def test_update_assessment_requires_an_existing_assessment(
    db, db_patient, minimal_payload
) -> None:
    """Updating before submitting raises instead of creating a row."""
    with pytest.raises(AssessmentNotFoundError):
        update_assessment(db, db_patient.id, _update_payload(minimal_payload))


def test_replace_assessment_overwrites_everything(
    db, db_patient, survey_payload, minimal_payload
) -> None:
    """PUT semantics: the payload is the complete new state."""
    create_assessment(db, db_patient.id, _create_payload(survey_payload))

    assessment = replace_assessment(
        db, db_patient.id, _create_payload(minimal_payload)
    )

    assert assessment.age == 45
    assert assessment.current_symptoms == []
    assert assessment.medications == []
    assert assessment.allergies == []
    assert assessment.additional_information is None
    assert [item.condition for item in assessment.medical_history] == [
        MedicalConditionType.none
    ]
    assert assessment.status is AssessmentStatus.updated


def test_replace_assessment_requires_an_existing_assessment(
    db, db_patient, minimal_payload
) -> None:
    """PUT on a patient without a survey raises ``AssessmentNotFoundError``."""
    with pytest.raises(AssessmentNotFoundError):
        replace_assessment(db, db_patient.id, _create_payload(minimal_payload))