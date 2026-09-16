"""Persistence tests: survey data must survive new sessions and new API clients."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.main import app
from backend.models.health_assessment import (
    Allergy,
    CurrentSymptoms,
    HealthAssessment,
    Medication,
    MedicalCondition,
)

ASSESSMENTS = "/api/v1/assessments"


def test_answers_are_stored_in_normalised_child_tables(
    client, auth_headers, survey_payload, submit_survey, patient, db
) -> None:
    """Every repeating answer gets its own row instead of a JSON blob."""
    submit_survey(auth_headers, survey_payload)

    assessment = db.scalar(
        select(HealthAssessment).where(
            HealthAssessment.patient_id == patient["patient_id"]
        )
    )
    assert assessment is not None
    assert assessment.age == 34
    assert assessment.bmi == 22.77
    assert assessment.additional_information == "Family history of hypertension."

    counts = {
        "conditions": db.scalar(select(func.count()).select_from(MedicalCondition)),
        "symptoms": db.scalar(select(func.count()).select_from(CurrentSymptoms)),
        "medications": db.scalar(select(func.count()).select_from(Medication)),
        "allergies": db.scalar(select(func.count()).select_from(Allergy)),
    }
    assert counts == {
        "conditions": 2,
        "symptoms": 2,
        "medications": 1,
        "allergies": 1,
    }


def test_assessment_survives_a_new_client_and_a_new_login(
    client, patient_factory, survey_payload
) -> None:
    """Data written by one client/token is readable by a later one."""
    patient = patient_factory()
    created = client.post(
        ASSESSMENTS, json=survey_payload, headers=patient["headers"]
    ).json()

    # A brand new application instance simulates a process restart (file-backed DB).
    with TestClient(app) as second_client:
        login = second_client.post(
            "/api/v1/auth/login",
            json={"email": patient["email"], "password": "StrongPass123"},
        )
        assert login.status_code == 200, login.text
        new_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        fetched = second_client.get(f"{ASSESSMENTS}/me", headers=new_headers)
        assert fetched.status_code == 200
        assert fetched.json() == created


def test_updates_are_persisted_for_later_reads(
    client, auth_headers, minimal_payload, submit_survey
) -> None:
    """A PATCH is durable: a later GET (and a fresh login) sees the new values."""
    submit_survey(auth_headers, minimal_payload)
    client.patch(
        f"{ASSESSMENTS}/me",
        json={"additional_information": "Allergic to shellfish."},
        headers=auth_headers,
    )

    body = client.get(f"{ASSESSMENTS}/me", headers=auth_headers).json()

    assert body["additional_information"] == "Allergic to shellfish."
    assert body["status"] == "updated"

    # SQLite stores naive UTC timestamps, so normalise before comparing.
    updated_at = datetime.fromisoformat(body["updated_at"])
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    assert updated_at <= datetime.now(timezone.utc)


def test_deleting_the_assessment_removes_child_rows(
    client, auth_headers, survey_payload, submit_survey, db
) -> None:
    """Withdrawing the survey cleans up the normalised child tables."""
    submit_survey(auth_headers, survey_payload)

    assert client.delete(f"{ASSESSMENTS}/me", headers=auth_headers).status_code == 204

    db.expire_all()
    assert db.scalar(select(func.count()).select_from(HealthAssessment)) == 0
    assert db.scalar(select(func.count()).select_from(MedicalCondition)) == 0
    assert db.scalar(select(func.count()).select_from(CurrentSymptoms)) == 0
    assert db.scalar(select(func.count()).select_from(Medication)) == 0
    assert db.scalar(select(func.count()).select_from(Allergy)) == 0