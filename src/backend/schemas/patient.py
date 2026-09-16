"""Request/response schemas for patient registration and login.

Module 1 only needs enough identity to own a ``patient_id``; the survey itself is
stored in the assessment tables and never duplicates patient data.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.models.patient import Patient
from backend.schemas.fields import (
    PASSWORD_MAX_BYTES,
    FullName,
    OptionalText,
    Password,
    PhoneNumber,
)


class PatientRegister(BaseModel):
    """Payload used to create a patient account."""

    model_config = ConfigDict(extra="forbid")

    full_name: FullName = Field(description="Patient's full name.")
    email: EmailStr = Field(description="Unique e-mail used to sign in.")
    password: Password = Field(description="Password, at least 8 characters.")
    phone_number: OptionalText = Field(
        default=None, max_length=32, description="Optional contact number."
    )

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        """Reject blank and bcrypt-incompatible passwords."""
        if not value.strip():
            raise ValueError("password must not be blank")
        if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
            raise ValueError(
                f"password must not exceed {PASSWORD_MAX_BYTES} bytes when UTF-8 encoded"
            )
        return value

    @field_validator("phone_number")
    @classmethod
    def _validate_phone_number(cls, value: str | None) -> str | None:
        """Ensure an optional phone number is made of digits and separators."""
        if value is None:
            return None
        allowed = set("0123456789 +-()")
        if not set(value) <= allowed:
            raise ValueError("phone number may only contain digits, spaces, +, -, (, )")
        return value


class PatientLogin(BaseModel):
    """Payload used to authenticate a patient."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_BYTES)


class PatientRead(BaseModel):
    """Public representation of a patient account."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: int
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    created_at: datetime

    @classmethod
    def from_patient(cls, patient: Patient) -> "PatientRead":
        """Build the response model from a :class:`~backend.models.patient.Patient`."""
        return cls(
            patient_id=patient.id,
            full_name=patient.full_name,
            email=patient.email,
            phone_number=patient.phone_number,
            created_at=patient.created_at,
        )


class TokenResponse(BaseModel):
    """Bearer token returned by register/login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds.")
    patient: PatientRead