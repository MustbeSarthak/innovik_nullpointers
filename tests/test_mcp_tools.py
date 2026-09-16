"""Tests for the MCP tools that expose the health assessment data.

The tools are the boundary future agents use, so both the happy path (payload
shape) and the argument validation are covered.
"""

import pytest

from backend.mcp.tools import (
    get_health_assessment_status,
    get_health_assessment_summary,
    get_patient_health_assessment,
    list_assessed_patient_ids,
)
from backend.schemas.assessment import HealthAssessmentCreate
from backend.services.assessment_service import create_assessment


@pytest.fixture
def stored_assessment(db, db_patient, survey_payload):
    """A persisted assessment created through the service layer."""
    return create_assessment(
        db, db_patient.id, HealthAssessmentCreate.model_validate(survey_payload)
    )


def test_tool_returns_full_assessment(db, db_patient, stored_assessment) -> None:
    """``get_patient_health_assessment`` returns a JSON-ready profile."""
    result = get_patient_health_assessment(db_patient.id)

    assert result["found"] is True
    assert result["patient_id"] == db_patient.id
    assessment = result["assessment"]
    assert assessment["basic_information"]["age"] == 34
    assert assessment["basic_information"]["bmi"] == 22.77
    assert assessment["basic_information"]["bmi_category"] == "normal"
    assert assessment["medical_history"]["conditions"][0] == {
        "condition": "diabetes",
        "details": None,
    }
    assert assessment["current_symptoms"]["symptoms"][0]["severity"] == "moderate"
    assert assessment["medications"]["medications"][0]["name"] == "Metformin"
    assert assessment["allergies"]["allergies"][0]["allergen"] == "Penicillin"
    assert assessment["additional_information"] == "Family history of hypertension."
    assert isinstance(assessment["created_at"], str)


def test_tool_reports_missing_assessment(db, db_patient) -> None:
    """A patient without a survey is reported instead of raising."""
    result = get_patient_health_assessment(db_patient.id)

    assert result == {"found": False, "patient_id": db_patient.id, "assessment": None}


def test_summary_tool_exposes_risk_signals(
    db, db_patient, stored_assessment
) -> None:
    """The compact summary carries the signals the Risk agent needs."""
    result = get_health_assessment_summary(db_patient.id)

    assert result["found"] is True
    assert result["age"] == 34
    assert result["gender"] == "female"
    assert result["bmi_category"] == "normal"
    assert result["conditions"] == ["diabetes", "other"]
    assert result["symptom_count"] == 2
    assert result["worst_symptom_severity"] == "moderate"
    assert result["medication_count"] == 1
    assert result["allergy_count"] == 1
    assert result["has_allergies"] is True
    assert result["has_additional_information"] is True
    assert isinstance(result["updated_at"], str)


def test_summary_tool_reports_missing_assessment(db, db_patient) -> None:
    """Missing assessments are reported with ``found: False``."""
    assert get_health_assessment_summary(db_patient.id) == {
        "found": False,
        "patient_id": db_patient.id,
    }


def test_status_tool_reports_completion(db, db_patient, stored_assessment) -> None:
    """The status tool tells an agent whether the onboarding is complete."""
    result = get_health_assessment_status(db_patient.id)

    assert result["has_assessment"] is True
    assert result["status"] == "submitted"
    assert isinstance(result["submitted_at"], str)
    assert isinstance(result["updated_at"], str)


def test_status_tool_for_patient_without_assessment(db, db_patient) -> None:
    """An unfinished onboarding is flagged instead of raising."""
    assert get_health_assessment_status(db_patient.id) == {
        "patient_id": db_patient.id,
        "has_assessment": False,
    }


def test_list_assessed_patient_ids(db, stored_assessment, db_patient) -> None:
    """Only patients that submitted the survey are listed."""
    result = list_assessed_patient_ids()

    assert result["count"] == 1
    assert result["patient_ids"] == [db_patient.id]
    assert result["limit"] == 50


@pytest.mark.parametrize("invalid_id", [0, -3, "42", 2.5, None, True])
def test_tools_validate_patient_id(db_patient, invalid_id) -> None:
    """Non-positive or non-integer ids are rejected by the tool itself."""
    with pytest.raises(ValueError):
        get_patient_health_assessment(invalid_id)
    with pytest.raises(ValueError):
        get_health_assessment_summary(invalid_id)
    with pytest.raises(ValueError):
        get_health_assessment_status(invalid_id)


@pytest.mark.parametrize("invalid_limit", [0, -1, 201, "10", 2.5, None])
def test_list_tool_validates_limit(invalid_limit) -> None:
    """The listing tool refuses limits outside 1..200."""
    with pytest.raises(ValueError):
        list_assessed_patient_ids(invalid_limit)


def test_list_tool_accepts_lower_bound() -> None:
    """``limit=1`` is a valid request even when nothing is stored."""
    assert list_assessed_patient_ids(1) == {
        "count": 0,
        "limit": 1,
        "patient_ids": [],
    }