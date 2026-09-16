"""MCP tools exposing the Module 1 health assessment data.

These tools are the read-only contract for the future agents.  They hold no LLM
logic: each one validates its arguments, opens its own database session through
:func:`backend.core.database.session_scope` and returns plain JSON-serialisable
dictionaries.  Every docstring is written so it can be used verbatim as the MCP
tool description.
"""

from typing import Any

from sqlalchemy import select

from backend.core.database import session_scope
from backend.models.enums import SymptomSeverity
from backend.models.health_assessment import HealthAssessment
from backend.services.assessment_service import (
    bmi_category,
    get_assessment,
    to_read_model,
)

MAX_PATIENT_ID = 2_147_483_647
MAX_LIST_LIMIT = 200

# Ordering used to pick the most severe reported symptom.
_SEVERITY_ORDER: dict[SymptomSeverity, int] = {
    SymptomSeverity.mild: 1,
    SymptomSeverity.moderate: 2,
    SymptomSeverity.severe: 3,
}


def _validate_patient_id(patient_id: Any) -> int:
    """Validate a ``patient_id`` argument.

    Raises:
        ValueError: when the value is not a positive integer.
    """
    if isinstance(patient_id, bool) or not isinstance(patient_id, int):
        raise ValueError("patient_id must be an integer")
    if patient_id < 1 or patient_id > MAX_PATIENT_ID:
        raise ValueError(f"patient_id must be between 1 and {MAX_PATIENT_ID}")
    return patient_id


def _validate_limit(limit: Any) -> int:
    """Validate the ``limit`` argument of the listing tool."""
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if limit < 1 or limit > MAX_LIST_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIST_LIMIT}")
    return limit


def _assessment_payload(assessment: HealthAssessment) -> dict[str, Any]:
    """Serialise an assessment ORM row into a JSON-compatible dictionary."""
    return to_read_model(assessment).model_dump(mode="json")


def get_patient_health_assessment(patient_id: int) -> dict[str, Any]:
    """Fetch the complete health assessment (survey) of one patient.

    Use this tool when you need the patient's full onboarding answers: basic
    information, medical history, current symptoms, medications, allergies and the
    optional additional information they shared.

    Args:
        patient_id: Primary key of an existing patient record
            (``patients.patient_id``). Patient records are never created here.

    Returns:
        A dictionary with ``found`` (bool), ``patient_id`` and ``assessment``.
        ``assessment`` is ``None`` when the patient has not submitted the survey
        yet; otherwise it contains ``basic_information`` (age, gender, height_cm,
        weight_kg, bmi, bmi_category), ``medical_history``, ``current_symptoms``,
        ``medications``, ``allergies``, ``additional_information``, ``status``,
        ``created_at`` and ``updated_at``.

    Raises:
        ValueError: when ``patient_id`` is not a positive integer.
    """
    valid_id = _validate_patient_id(patient_id)
    with session_scope() as db:
        assessment = get_assessment(db, valid_id)
        if assessment is None:
            return {"found": False, "patient_id": valid_id, "assessment": None}
        return {
            "found": True,
            "patient_id": valid_id,
            "assessment": _assessment_payload(assessment),
        }


def get_health_assessment_summary(patient_id: int) -> dict[str, Any]:
    """Fetch a compact risk-oriented snapshot of a patient's health assessment.

    Prefer this tool over the full assessment when you only need high level
    signals (BMI category, existing conditions, worst symptom severity and
    medication/allergy counts) instead of every answer.

    Args:
        patient_id: Primary key of an existing patient record.

    Returns:
        A dictionary with ``found`` and, when the survey exists, ``age``,
        ``gender``, ``bmi``, ``bmi_category``, ``conditions`` (list of survey
        values), ``symptom_count``, ``worst_symptom_severity``,
        ``medication_count``, ``allergy_count``, ``has_allergies``,
        ``has_additional_information`` and ``updated_at``.

    Raises:
        ValueError: when ``patient_id`` is not a positive integer.
    """
    valid_id = _validate_patient_id(patient_id)
    with session_scope() as db:
        assessment = get_assessment(db, valid_id)
        if assessment is None:
            return {"found": False, "patient_id": valid_id}

        severities = [symptom.severity for symptom in assessment.current_symptoms]
        worst = max(severities, key=lambda value: _SEVERITY_ORDER[value], default=None)

        return {
            "found": True,
            "patient_id": valid_id,
            "age": assessment.age,
            "gender": assessment.gender.value,
            "bmi": assessment.bmi,
            "bmi_category": bmi_category(assessment.bmi) if assessment.bmi else None,
            "conditions": [
                item.condition.value for item in assessment.medical_history
            ],
            "symptom_count": len(assessment.current_symptoms),
            "worst_symptom_severity": worst.value if worst is not None else None,
            "medication_count": len(assessment.medications),
            "allergy_count": len(assessment.allergies),
            "has_allergies": bool(assessment.allergies),
            "has_additional_information": bool(assessment.additional_information),
            "updated_at": assessment.updated_at.isoformat()
            if assessment.updated_at
            else None,
        }


def get_health_assessment_status(patient_id: int) -> dict[str, Any]:
    """Check whether a patient has completed the health assessment survey.

    Use this before running any downstream reasoning so an incomplete profile is
    detected early.

    Args:
        patient_id: Primary key of an existing patient record.

    Returns:
        A dictionary with ``patient_id``, ``has_assessment`` (bool) and, when
        available, ``status``, ``submitted_at`` and ``updated_at`` (ISO-8601).

    Raises:
        ValueError: when ``patient_id`` is not a positive integer.
    """
    valid_id = _validate_patient_id(patient_id)
    with session_scope() as db:
        assessment = get_assessment(db, valid_id)
        if assessment is None:
            return {"patient_id": valid_id, "has_assessment": False}
        return {
            "patient_id": valid_id,
            "has_assessment": True,
            "status": assessment.status.value,
            "submitted_at": assessment.created_at.isoformat()
            if assessment.created_at
            else None,
            "updated_at": assessment.updated_at.isoformat()
            if assessment.updated_at
            else None,
        }


def list_assessed_patient_ids(limit: int = 50) -> dict[str, Any]:
    """List the patient ids that already submitted a health assessment.

    Intended for the Monitoring agent, which needs to iterate over patients with a
    complete profile.

    Args:
        limit: Maximum number of ids to return, between 1 and 200 (default 50).

    Returns:
        A dictionary with ``count``, ``limit`` and ``patient_ids``, ordered by the
        most recently updated assessment first.

    Raises:
        ValueError: when ``limit`` is not an integer between 1 and 200.
    """
    valid_limit = _validate_limit(limit)
    with session_scope() as db:
        rows = db.scalars(
            select(HealthAssessment.patient_id)
            .order_by(HealthAssessment.updated_at.desc())
            .limit(valid_limit)
        ).all()
        return {"count": len(rows), "limit": valid_limit, "patient_ids": list(rows)}


# Tools registered on the FastMCP server (see ``backend.mcp.server``).
TOOL_FUNCTIONS = (
    get_patient_health_assessment,
    get_health_assessment_summary,
    get_health_assessment_status,
    list_assessed_patient_ids,
)
