"""Shared fixtures for the Healthcare Assistant backend test-suite.

The tests run against a temporary SQLite file.  ``DATABASE_URL`` is set *before*
any backend module is imported because the SQLAlchemy engine is created at import
time from the cached settings object.
"""

import os
import tempfile
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

_TEMP_DIR = Path(tempfile.mkdtemp(prefix="ha-module1-tests-"))
_DB_PATH = (_TEMP_DIR / "test_healthcare_assistant.db").as_posix()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DEBUG"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend import models  # noqa: E402,F401  (registers tables on Base.metadata)
from backend.core.database import Base, SessionLocal, engine  # noqa: E402
from backend.main import app  # noqa: E402
from backend.schemas.patient import PatientRegister  # noqa: E402
from backend.services.patient_service import register_patient  # noqa: E402

TEST_PASSWORD = "StrongPass123"


@pytest.fixture(autouse=True)
def fresh_schema() -> Iterator[None]:
    """Recreate the schema before every test so tests stay independent."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    """A session bound to the temporary test database."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A FastAPI test client (its lifespan hook also creates the schema)."""
    with TestClient(app) as test_client:
        yield test_client


def unique_email(prefix: str = "patient") -> str:
    """Return an e-mail address that is unique within the test session."""
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def patient_factory(client: TestClient) -> Callable[..., dict[str, object]]:
    """Register and log in patients, returning ids and bearer tokens."""

    def _create(
        email: str | None = None,
        full_name: str = "Test Patient",
        phone_number: str | None = "+1 555 0100",
    ) -> dict[str, object]:
        address = email or unique_email()
        response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": full_name,
                "email": address,
                "password": TEST_PASSWORD,
                "phone_number": phone_number,
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        token = body["access_token"]
        return {
            "patient_id": body["patient"]["patient_id"],
            "email": address,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    return _create


@pytest.fixture
def patient(patient_factory: Callable[..., dict[str, object]]) -> dict[str, object]:
    """A registered, logged-in patient."""
    return patient_factory()


@pytest.fixture
def auth_headers(patient: dict[str, object]) -> dict[str, str]:
    """Bearer-token headers of :func:`patient`."""
    return patient["headers"]  # type: ignore[return-value]


def register_patient_row(db: Session, email: str | None = None):
    """Create a patient directly through the service layer."""
    return register_patient(
        db,
        PatientRegister(
            full_name="Service Level Patient",
            email=email or unique_email("service"),
            password=TEST_PASSWORD,
            phone_number=None,
        ),
    )


@pytest.fixture
def survey_payload() -> dict[str, object]:
    """A complete, valid survey submission (all six steps filled in)."""
    return {
        "basic_information": {
            "age": 34,
            "gender": "female",
            "height_cm": 165.0,
            "weight_kg": 62.0,
        },
        "medical_history": {
            "conditions": [
                {"condition": "diabetes", "details": None},
                {"condition": "other", "details": "Migraine with aura"},
            ]
        },
        "current_symptoms": {
            "symptoms": [
                {
                    "symptom": "Persistent headache",
                    "duration": "3 days",
                    "severity": "moderate",
                    "notes": "Worse in the evening",
                },
                {
                    "symptom": "Fatigue",
                    "duration": "1 week",
                    "severity": "mild",
                    "notes": None,
                },
            ]
        },
        "medications": {
            "medications": [
                {"name": "Metformin", "dosage": "500 mg", "frequency": "twice daily"}
            ]
        },
        "allergies": {
            "allergies": [{"allergen": "Penicillin", "description": "Skin rash"}]
        },
        "additional_information": "Family history of hypertension.",
    }


@pytest.fixture
def minimal_payload() -> dict[str, object]:
    """The smallest valid submission: the two required steps only."""
    return {
        "basic_information": {
            "age": 45,
            "gender": "prefer_not_to_say",
            "height_cm": 180.0,
            "weight_kg": 95.5,
        },
        "medical_history": {"conditions": [{"condition": "none"}]},
    }


@pytest.fixture
def submit_survey(client: TestClient) -> Callable[..., dict[str, object]]:
    """Submit a survey through the API and return the created response body."""

    def _submit(
        headers: dict[str, str], payload: dict[str, object]
    ) -> dict[str, object]:
        response = client.post("/api/v1/assessments", json=payload, headers=headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _submit


@pytest.fixture
def db_patient(db: Session):
    """A patient row created through the service layer (no HTTP involved)."""
    return register_patient_row(db)