"""Reusable validated field types and shared bounds for the API schemas.

Keeping the bounds here means the survey limits are declared once and reused by
request models, response models and the survey-metadata endpoint.
"""

from typing import Annotated, Any

from pydantic import BeforeValidator, StringConstraints

# --------------------------------------------------------------------------
# Basic information bounds (mirrored by CHECK constraints in the ORM models)
# --------------------------------------------------------------------------
AGE_MIN, AGE_MAX = 0, 120
HEIGHT_MIN_CM, HEIGHT_MAX_CM = 30.0, 250.0
WEIGHT_MIN_KG, WEIGHT_MAX_KG = 2.0, 500.0

# --------------------------------------------------------------------------
# Text limits per survey field
# --------------------------------------------------------------------------
ADDITIONAL_INFORMATION_MAX_LENGTH = 2000
MAX_SYMPTOMS = 30
MAX_MEDICATIONS = 50
MAX_ALLERGIES = 50
MAX_CONDITIONS = 20

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72


def _blank_to_none(value: Any) -> Any:
    """Convert whitespace-only optional answers into ``None``.

    Patients frequently leave optional inputs blank; normalising them here keeps
    "not answered" distinguishable from a real empty string in the database.
    """
    if isinstance(value, str) and not value.strip():
        return None
    return value


# Optional free-text answer: trimmed first, blank becomes ``None``.
OptionalText = Annotated[str | None, BeforeValidator(_blank_to_none)]

# Required short answer: trimmed, never blank.
ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
MediumText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
LongText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
# Conditional / descriptive answers (condition details, notes) may be longer.
ConditionDetails = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]
# Supporting notes attached to a symptom or allergy.
NotesText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]

FullName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)
]
PhoneNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=6, max_length=32),
]
Password = Annotated[
    str, StringConstraints(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_BYTES)
]