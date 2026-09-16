"""End-to-end tests for the Module 1 health assessment API.

Covered: successful submission, validation errors, update (PATCH/PUT),
retrieval, optional fields, authorization and persistence.
"""

from datetime import datetime

from sqlalchemy import select

from backend.models.health_assessment import HealthAssessment

ASSESSMENTS = "/api/v1/assessments"


# --------------------------------------------------------------------------
# Successful submission
# --------------------------------------------------------------------------
def test_submit_health_assessment_persists_every_section(
    client, auth_headers, survey_payload, patient
) -> None:
    """A complete survey is stored and echoed back with derived values."""
    response = client.post(ASSESSMENTS, json=survey_payload, headers=auth_headers)

    assert response.status_code == 201, response.text
    body = response.json()

    assert body["patient_id"] == patient["patient_id"]
    assert body["status"] == "submitted"
    assert body["basic_information"] == {
        "age": 34,
        "gender": "female",
        "height_cm": 165.0,
        "weight_kg": 62.0,
        "bmi": 22.77,
        "bmi_category": "normal",
    }
    assert body["medical_history"]["conditions"] == [
        {"condition": "diabetes", "details": None},
        {"condition": "other", "details": "Migraine with aura"},
    ]
    assert [symptom["symptom"] for symptom in body["current_symptoms"]["symptoms"]] == [
        "Persistent headache",
        "Fatigue",
    ]
    assert body["current_symptoms"]["symptoms"][0]["severity"] == "moderate"
    assert body["medications"]["medications"] == [
        {"name": "Metformin", "dosage": "500 mg", "frequency": "twice daily"}
    ]
    assert body["allergies"]["allergies"] == [
        {"allergen": "Penicillin", "description": "Skin rash"}
    ]
    assert body["additional_information"] == "Family history of hypertension."

    # Timestamps must be serialisable ISO-8601 values.
    datetime.fromisoformat(body["created_at"])
    datetime.fromisoformat(body["updated_at"])


def test_submission_keeps_one_patient_record(
    client, auth_headers, survey_payload, patient, db
) -> None:
    """Submitting the survey never creates a second patient / assessment row."""
    client.post(ASSESSMENTS, json=survey_payload, headers=auth_headers)

    rows = db.scalars(select(HealthAssessment)).all()
    assert len(rows) == 1
    assert rows[0].patient_id == patient["patient_id"]

    profile = client.get("/api/v1/auth/me", headers=auth_headers)
    assert profile.status_code == 200
    assert profile.json()["patient_id"] == patient["patient_id"]


def test_duplicate_submission_is_rejected(client, auth_headers, survey_payload) -> None:
    """A patient can only submit the survey once; the second POST returns 409."""
    assert (
        client.post(ASSESSMENTS, json=survey_payload, headers=auth_headers).status_code
        == 201
    )

    response = client.post(ASSESSMENTS, json=survey_payload, headers=auth_headers)

    assert response.status_code == 409
    assert "already has a health assessment" in response.json()["detail"]
    assert "PATCH" in response.json()["hint"]


def test_optional_sections_may_be_omitted(client, auth_headers, minimal_payload) -> None:
    """Required-only payload: optional sections default to empty, text to null."""
    response = client.post(ASSESSMENTS, json=minimal_payload, headers=auth_headers)

    assert response.status_code == 201, response.text
    body = response.json()

    assert body["current_symptoms"] == {"symptoms": []}
    assert body["medications"] == {"medications": []}
    assert body["allergies"] == {"allergies": []}
    assert body["additional_information"] is None
    assert body["basic_information"]["bmi_category"] == "overweight"


def test_blank_optional_strings_are_normalised_to_null(
    client, auth_headers, minimal_payload
) -> None:
    """Whitespace-only optional answers are stored as "not answered"."""
    payload = dict(minimal_payload)
    payload["additional_information"] = "   "
    payload["current_symptoms"] = {
        "symptoms": [
            {
                "symptom": "Dry cough",
                "duration": "2 weeks",
                "severity": "mild",
                "notes": "  ",
            }
        ]
    }
    payload["medications"] = {
        "medications": [{"name": "Vitamin D", "dosage": "1000 IU", "frequency": "daily"}]
    }
    payload["allergies"] = {
        "allergies": [{"allergen": "Dust", "description": "  "}]
    }

    response = client.post(ASSESSMENTS, json=payload, headers=auth_headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["additional_information"] is None
    assert body["current_symptoms"]["symptoms"][0]["notes"] is None
    assert body["allergies"]["allergies"][0]["description"] is None
    assert body["medications"]["medications"][0]["name"] == "Vitamin D"


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------
def test_retrieve_own_assessment(
    client, auth_headers, survey_payload, submit_survey
) -> None:
    """GET /assessments/me returns exactly what was submitted."""
    created = submit_survey(auth_headers, survey_payload)

    response = client.get(f"{ASSESSMENTS}/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == created


def test_retrieve_assessment_by_patient_id(
    client, auth_headers, patient, survey_payload, submit_survey
) -> None:
    """GET /assessments/patient/{id} works for the owning patient."""
    submit_survey(auth_headers, survey_payload)

    response = client.get(
        f"{ASSESSMENTS}/patient/{patient['patient_id']}", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["patient_id"] == patient["patient_id"]


def test_cannot_read_another_patients_assessment(
    client, auth_headers, patient, patient_factory, survey_payload, submit_survey
) -> None:
    """A patient may not read an assessment that belongs to somebody else."""
    submit_survey(auth_headers, survey_payload)
    other = patient_factory()

    response = client.get(
        f"{ASSESSMENTS}/patient/{patient['patient_id']}", headers=other["headers"]
    )

    assert response.status_code == 403
    assert "your own" in response.json()["detail"]


def test_retrieval_before_submission_returns_404(client, auth_headers) -> None:
    """A patient without a survey gets a clear 404 with a hint."""
    response = client.get(f"{ASSESSMENTS}/me", headers=auth_headers)

    assert response.status_code == 404
    assert "has not submitted" in response.json()["detail"]
    assert "POST" in response.json()["hint"]


def test_assessment_endpoints_require_authentication(client, survey_payload) -> None:
    """Missing credentials are rejected with 401 on every protected endpoint."""
    assert client.post(ASSESSMENTS, json=survey_payload).status_code == 401
    assert client.get(f"{ASSESSMENTS}/me").status_code == 401
    assert client.patch(f"{ASSESSMENTS}/me", json={}).status_code == 401
    assert client.put(f"{ASSESSMENTS}/me", json=survey_payload).status_code == 401

    bad_token = {"Authorization": "Bearer not-a-real-token"}
    assert client.get(f"{ASSESSMENTS}/me", headers=bad_token).status_code == 401


# --------------------------------------------------------------------------
# Updates
# --------------------------------------------------------------------------
def test_patch_updates_only_the_provided_section(
    client, auth_headers, survey_payload, submit_survey
) -> None:
    """PATCH replaces one section, keeps the others and bumps the status."""
    submit_survey(auth_headers, survey_payload)

    response = client.patch(
        f"{ASSESSMENTS}/me",
        json={"allergies": {"allergies": [{"allergen": "Peanuts"}]}},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["allergies"]["allergies"] == [
        {"allergen": "Peanuts", "description": None}
    ]
    assert body["status"] == "updated"
    # untouched sections survive the partial update
    assert body["medical_history"]["conditions"][0]["condition"] == "diabetes"
    assert body["medications"]["medications"][0]["name"] == "Metformin"
    assert body["additional_information"] == "Family history of hypertension."


def test_patch_basic_information_recalculates_bmi(
    client, auth_headers, minimal_payload, submit_survey
) -> None:
    """Changing height/weight recomputes the derived BMI values."""
    submit_survey(auth_headers, minimal_payload)

    response = client.patch(
        f"{ASSESSMENTS}/me",
        json={
            "basic_information": {
                "age": 45,
                "gender": "prefer_not_to_say",
                "height_cm": 180.0,
                "weight_kg": 60.0,
            }
        },
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["basic_information"]["bmi"] == 18.52
    assert response.json()["basic_information"]["bmi_category"] == "normal"


def test_patch_can_clear_optional_free_text(
    client, auth_headers, survey_payload, submit_survey
) -> None:
    """Sending null for additional_information clears the field."""
    submit_survey(auth_headers, survey_payload)

    response = client.patch(
        f"{ASSESSMENTS}/me",
        json={"additional_information": None},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["additional_information"] is None


def test_patch_without_payload_is_rejected(
    client, auth_headers, minimal_payload, submit_survey
) -> None:
    """An empty PATCH body is a validation error rather than a silent no-op."""
    submit_survey(auth_headers, minimal_payload)

    response = client.patch(f"{ASSESSMENTS}/me", json={}, headers=auth_headers)

    assert response.status_code == 422
    assert "at least one survey section" in response.json()["errors"][0]["message"]


def test_put_replaces_the_whole_assessment(
    client, auth_headers, survey_payload, minimal_payload, submit_survey
) -> None:
    """PUT overwrites every section, so omitted optional data is removed."""
    submit_survey(auth_headers, survey_payload)

    response = client.put(
        f"{ASSESSMENTS}/me", json=minimal_payload, headers=auth_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["basic_information"]["age"] == 45
    assert body["medical_history"]["conditions"] == [
        {"condition": "none", "details": None}
    ]
    assert body["current_symptoms"] == {"symptoms": []}
    assert body["medications"] == {"medications": []}
    assert body["allergies"] == {"allergies": []}
    assert body["additional_information"] is None


def test_update_before_submission_returns_404(
    client, auth_headers, minimal_payload
) -> None:
    """Updating a non-existent assessment is a 404, not an implicit create."""
    patch_response = client.patch(
        f"{ASSESSMENTS}/me",
        json={"additional_information": "hello"},
        headers=auth_headers,
    )
    put_response = client.put(
        f"{ASSESSMENTS}/me", json=minimal_payload, headers=auth_headers
    )

    assert patch_response.status_code == 404
    assert put_response.status_code == 404


def test_delete_withdraws_the_assessment_but_keeps_the_patient(
    client, auth_headers, minimal_payload, submit_survey
) -> None:
    """DELETE removes the survey while the patient account stays intact."""
    submit_survey(auth_headers, minimal_payload)

    assert client.delete(f"{ASSESSMENTS}/me", headers=auth_headers).status_code == 204
    assert client.get(f"{ASSESSMENTS}/me", headers=auth_headers).status_code == 404
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 200
    assert client.delete(f"{ASSESSMENTS}/me", headers=auth_headers).status_code == 404