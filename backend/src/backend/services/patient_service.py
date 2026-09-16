"""Patient account operations (registration and authentication).

Patients are the only identity in the system, so this module is the single
place that creates a ``patient_id``.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.exceptions import PatientAlreadyExistsError, PatientNotFoundError
from backend.core.security import hash_password, verify_password
from backend.models.patient import Patient
from backend.schemas.patient import PatientRegister


def normalize_email(email: str) -> str:
    """Return the canonical storage form of an e-mail address."""
    return email.strip().lower()


def get_patient_by_email(db: Session, email: str) -> Patient | None:
    """Return the patient with ``email`` or ``None`` when it does not exist."""
    return db.scalar(select(Patient).where(Patient.email == normalize_email(email)))


def get_patient(db: Session, patient_id: int) -> Patient:
    """Return the patient with ``patient_id``.

    Raises:
        PatientNotFoundError: when no such patient exists.
    """
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise PatientNotFoundError(f"patient {patient_id} was not found")
    return patient


def register_patient(db: Session, payload: PatientRegister) -> Patient:
    """Create a new patient account.

    Raises:
        PatientAlreadyExistsError: when the e-mail address is already registered.
    """
    email = normalize_email(payload.email)
    if get_patient_by_email(db, email) is not None:
        raise PatientAlreadyExistsError(f"e-mail {email} is already registered")

    patient = Patient(
        full_name=payload.full_name,
        email=email,
        hashed_password=hash_password(payload.password),
        phone_number=payload.phone_number,
    )
    db.add(patient)
    try:
        db.commit()
    except IntegrityError as exc:  # concurrent registration race
        db.rollback()
        raise PatientAlreadyExistsError(
            f"e-mail {email} is already registered"
        ) from exc
    db.refresh(patient)
    return patient


def authenticate_patient(db: Session, email: str, password: str) -> Patient | None:
    """Return the matching patient for valid credentials, else ``None``."""
    patient = get_patient_by_email(db, email)
    if patient is None or not verify_password(password, patient.hashed_password):
        return None
    return patient