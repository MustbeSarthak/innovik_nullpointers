"""Shared enumerations for patients and health assessments.

Every member value is lower_snake_case and identical to its name so that the
SQLAlchemy ``Enum`` type stores predictable strings in the database.
"""

from enum import Enum


class Gender(str, Enum):
    """Gender values accepted by the health assessment survey."""

    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class MedicalConditionType(str, Enum):
    """Selectable entries of the survey's *Medical History* section.

    ``none`` means "no known existing condition" and must be the only entry
    when selected.  ``other`` requires free-text details.
    """

    diabetes = "diabetes"
    hypertension = "hypertension"
    asthma = "asthma"
    heart_related = "heart_related"
    kidney_related = "kidney_related"
    allergies = "allergies"
    other = "other"
    none = "none"


class SymptomSeverity(str, Enum):
    """Severity scale used for each reported symptom."""

    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class AssessmentStatus(str, Enum):
    """Lifecycle state of a patient's health assessment."""

    submitted = "submitted"
    updated = "updated"
