"""Input-validation tests for the health assessment API.

Every rule below is enforced by the Pydantic schemas, so the API answers with a
422 and a machine-readable ``errors`` list instead of storing bad data.
"""

import copy

import pytest

ASSESSMENTS = "/api/v1/assessments"

_MISSING = object()


def _apply(payload: dict, path: tuple, value) -> None:
    """Set ``path`` to ``value``; delete the key when value is ``_MISSING``."""
    target = payload
    for key in path[:-1]:
        target = target[key]
    if value is _MISSING:
        del target[path[-1]]
    else:
        target[path[-1]] = value


INVALID_CASES = [
    ("age_too_high", ("basic_information", "age"), 150, "basic_information.age"),
    ("age_negative", ("basic_information", "age"), -1, "basic_information.age"),
    ("age_not_a_number", ("basic_information", "age"), "thirty", "basic_information.age"),
    ("age_missing", ("basic_information", "age"), _MISSING, "basic_information.age"),
    ("unsupported_gender", ("basic_information", "gender"), "unknown", "basic_information.gender"),
    ("height_too_low", ("basic_information", "height_cm"), 5.0, "basic_information.height_cm"),
    ("height_too_high", ("basic_information", "height_cm"), 400.0, "basic_information.height_cm"),
    ("weight_too_low", ("basic_information", "weight_kg"), 0.5, "basic_information.weight_kg"),
    ("weight_too_high", ("basic_information", "weight_kg"), 900.0, "basic_information.weight_kg"),
    ("basic_information_missing", ("basic_information",), _MISSING, "basic_information"),
    ("medical_history_missing", ("medical_history",), _MISSING, "medical_history"),
    ("conditions_empty", ("medical_history", "conditions"), [], "medical_history.conditions"),
    (
        "unknown_condition",
        ("medical_history", "conditions"),
        [{"condition": "cancer"}],
        "medical_history.conditions.0.condition",
    ),
]


@pytest.mark.parametrize(
    ("path", "value", "expected_field"),
    [case[1:] for case in INVALID_CASES],
    ids=[case[0] for case in INVALID_CASES],
)
def test_invalid_answers_are_rejected(
    client, auth_headers, survey_payload, path, value, expected_field
) -> None:
    """Out-of-range values and bad vocabularies produce a 422 with the field path."""
    payload = copy.deepcopy(survey_payload)
    _apply(payload, path, value)

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["detail"] == "Validation failed for the submitted health assessment"
    assert expected_field in [error["field"] for error in body["errors"]]


STRUCTURAL_CASES = [
    (
        "none_combined_with_condition",
        ("medical_history", "conditions"),
        [{"condition": "none"}, {"condition": "diabetes"}],
        "none",
    ),
    (
        "duplicate_condition",
        ("medical_history", "conditions"),
        [{"condition": "asthma"}, {"condition": "asthma"}],
        "more than once",
    ),
    (
        "other_without_details",
        ("medical_history", "conditions"),
        [{"condition": "other"}],
        "requires the details",
    ),
    (
        "other_with_blank_details",
        ("medical_history", "conditions"),
        [{"condition": "other", "details": "   "}],
        "requires the details",
    ),
    (
        "unsupported_severity",
        ("current_symptoms", "symptoms"),
        [{"symptom": "Cough", "duration": "2 days", "severity": "extreme"}],
        "current_symptoms.symptoms.0.severity",
    ),
    (
        "blank_symptom",
        ("current_symptoms", "symptoms"),
        [{"symptom": "   ", "duration": "2 days", "severity": "mild"}],
        "current_symptoms.symptoms.0.symptom",
    ),
    (
        "undefined_symptom_duration",
        ("current_symptoms", "symptoms"),
        [{"symptom": "Cough", "severity": "mild"}],
        "current_symptoms.symptoms.0.duration",
    ),
    (
        "blank_medication_name",
        ("medications", "medications"),
        [{"name": "", "dosage": "10 mg", "frequency": "daily"}],
        "medications.medications.0.name",
    ),
    (
        "undefined_medication_dosage",
        ("medications", "medications"),
        [{"name": "Aspirin", "frequency": "daily"}],
        "medications.medications.0.dosage",
    ),
    (
        "blank_allergen",
        ("allergies", "allergies"),
        [{"allergen": " "}],
        "allergies.allergies.0.allergen",
    ),
]


@pytest.mark.parametrize(
    ("path", "value", "expected_message"),
    [case[1:] for case in STRUCTURAL_CASES],
    ids=[case[0] for case in STRUCTURAL_CASES],
)
def test_contradictory_or_incomplete_answers_are_rejected(
    client, auth_headers, survey_payload, path, value, expected_message
) -> None:
    """Cross-field rules keep the stored survey consistent."""
    payload = copy.deepcopy(survey_payload)
    _apply(payload, path, value)

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 422, response.text
    errors = response.json()["errors"]
    haystack = " ".join(
        f"{error['field']}: {error['message']}" for error in errors
    )
    assert expected_message in haystack


def test_unknown_fields_are_rejected(
    client, auth_headers, survey_payload
) -> None:
    """Unexpected keys are refused so typos never silently drop an answer."""
    payload = copy.deepcopy(survey_payload)
    payload["basic_information"]["blood_type"] = "O+"

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 422
    assert "blood_type" in response.json()["errors"][0]["field"]


def test_unknown_section_is_rejected(client, auth_headers, survey_payload) -> None:
    """An unknown top-level section fails validation as well."""
    payload = copy.deepcopy(survey_payload)
    payload["insurance"] = {"provider": "ACME"}

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 422
    assert "insurance" in response.json()["errors"][0]["field"]


def test_too_many_conditions_are_rejected(
    client, auth_headers, survey_payload
) -> None:
    """The Medical History list is capped to keep the payload reasonable."""
    payload = copy.deepcopy(survey_payload)
    payload["medical_history"]["conditions"] = [
        {"condition": "asthma", "details": f"note {index}"} for index in range(25)
    ]

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "medical_history.conditions"


def test_too_many_symptoms_are_rejected(client, auth_headers, survey_payload) -> None:
    """The symptom list is capped as well."""
    payload = copy.deepcopy(survey_payload)
    payload["current_symptoms"]["symptoms"] = [
        {"symptom": f"Symptom {index}", "duration": "1 day", "severity": "mild"}
        for index in range(31)
    ]

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "current_symptoms.symptoms"


def test_additional_information_length_is_enforced(
    client, auth_headers, survey_payload
) -> None:
    """The optional free-text field has a hard upper bound."""
    payload = copy.deepcopy(survey_payload)
    payload["additional_information"] = "x" * 2001

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "additional_information"


def test_additional_information_at_the_limit_is_accepted(
    client, auth_headers, minimal_payload
) -> None:
    """Exactly at the limit is still a valid answer."""
    payload = copy.deepcopy(minimal_payload)
    payload["additional_information"] = "x" * 2000

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 201, response.text
    assert len(response.json()["additional_information"]) == 2000


def test_missing_body_is_rejected(client, auth_headers) -> None:
    """An empty body cannot create an assessment."""
    response = client.post(ASSESSMENTS, json={}, headers=auth_headers)

    assert response.status_code == 422
    fields = {error["field"] for error in response.json()["errors"]}
    assert {"basic_information", "medical_history"} <= fields


def test_non_integer_patient_id_in_path_is_rejected(
    client, auth_headers
) -> None:
    """The path parameter itself is validated."""
    response = client.get(f"{ASSESSMENTS}/patient/not-an-id", headers=auth_headers)

    assert response.status_code == 422