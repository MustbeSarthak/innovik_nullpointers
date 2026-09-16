"""Shared FastAPI dependencies.

``get_db`` is re-exported from the core database module so routers import
everything they need from the API layer, while tests can still override a single
dependency to point at a temporary database.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.exceptions import PatientNotFoundError
from backend.core.security import SecurityError, decode_access_token
from backend.models.patient import Patient
from backend.services.patient_service import get_patient

# ``auto_error=False`` lets the endpoint return a consistent 401 payload
# instead of FastAPI's default 403 for a missing header.
bearer_scheme = HTTPBearer(auto_error=False, description="Patient access token")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_patient(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> Patient:
    """Return the patient identified by the bearer token.

    Raises:
        HTTPException: 401 when the token is missing/invalid or the patient no
            longer exists.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.credentials:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except SecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if subject is None or not str(subject).isdigit():
        raise unauthorized

    try:
        return get_patient(db, int(subject))
    except PatientNotFoundError as exc:
        raise unauthorized from exc


CurrentPatient = Annotated[Patient, Depends(get_current_patient)]