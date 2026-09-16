"""Patient registration and login endpoints.

Registration returns a bearer token straight away so a patient can move on to the
health assessment survey without a second round-trip.
"""

from fastapi import APIRouter, HTTPException, status

from backend.api.deps import CurrentPatient, DbSession
from backend.core.config import settings
from backend.core.security import create_access_token
from backend.models.patient import Patient
from backend.schemas.patient import (
    PatientLogin,
    PatientRead,
    PatientRegister,
    TokenResponse,
)
from backend.services.patient_service import authenticate_patient, register_patient

router = APIRouter(prefix="/auth", tags=["Patient Authentication"])


def _build_token_response(patient: Patient) -> TokenResponse:
    """Create a bearer token response for ``patient``."""
    return TokenResponse(
        access_token=create_access_token(patient.id),
        expires_in=settings.access_token_expire_minutes * 60,
        patient=PatientRead.from_patient(patient),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient",
    responses={409: {"description": "E-mail address already registered"}},
)
def register_patient_endpoint(
    payload: PatientRegister, db: DbSession
) -> TokenResponse:
    """Create the patient account that owns the health assessment."""
    patient = register_patient(db, payload)
    return _build_token_response(patient)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in as a patient",
    responses={401: {"description": "Invalid e-mail or password"}},
)
def login_endpoint(payload: PatientLogin, db: DbSession) -> TokenResponse:
    """Authenticate a patient and return a bearer token."""
    patient = authenticate_patient(db, payload.email, payload.password)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect e-mail or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _build_token_response(patient)


@router.get(
    "/me",
    response_model=PatientRead,
    summary="Read the signed-in patient",
    responses={401: {"description": "Missing or invalid token"}},
)
def read_current_patient(patient: CurrentPatient) -> PatientRead:
    """Return the profile of the authenticated patient."""
    return PatientRead.from_patient(patient)