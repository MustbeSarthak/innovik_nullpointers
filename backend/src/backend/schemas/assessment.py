"""Health assessment (survey) schemas — Module 1.

The request models mirror the six survey steps and validate every answer:

1. Basic Information   -> :class:`BasicInformation`
2. Medical History     -> :class:`MedicalHistorySection`
3. Current Symptoms    -> :class:`CurrentSymptomsSection`
4. Medications         -> :class:`MedicationsSection`
5. Allergies           -> :class:`AllergiesSection`
6. Review & Submit     -> :class:`HealthAssessmentCreate` (all sections together)

``additional_information`` is the optional free-text field belonging to step 5/6.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.models.enums import (
    AssessmentStatus,
    Gender,
    MedicalConditionType,
    SymptomSeverity,
)
from backend.schemas.fields import (
    ADDITIONAL_INFORMATION_MAX_LENGTH,
    AGE_MAX,
    AGE_MIN,
    HEIGHT_MAX_CM,
    HEIGHT_MIN_CM,
    MAX_ALLERGIES,
    MAX_CONDITIONS,
    MAX_MEDICATIONS,
    MAX_SYMPTOMS,
    WEIGHT_MAX_KG,
    WEIGHT_MIN_KG,
    LongText,
    MediumText,
    OptionalText,
    ShortText,
)



# --------------------------------------------------------------------------
# Step 1 - Basic Information
# --------------------------------------------------------------------------
class BasicInformation(BaseModel):
    """Basic Information section of the survey."""

    model_config = ConfigDict(extra="forbid")

    age: int = Field(ge=AGE_MIN, le=AGE_MAX, description="Age in years.")
    gender: Gender = Field(description="One of the supported gender values.")
    height_cm: float = Field(
        ge=HEIGHT_MIN_CM, le=HEIGHT_MAX_CM, description="Height in centimetres."
    )
    weight_kg: float = Field(
        ge=WEIGHT_MIN_KG, le=WEIGHT_MAX_KG, description="Weight in kilograms."
    )


# --------------------------------------------------------------------------
# Step 2 - Medical History
# --------------------------------------------------------------------------
class MedicalConditionItem(BaseModel):
    """One selected entry of the Medical History section."""

    model_config = ConfigDict(extra="forbid")

    condition: MedicalConditionType = Field(
        description="Existing condition the patient selected. These are survey "
        "options and are never assumed to be present."
    )
    details: OptionalText = Field(
        default=None,
        max_length=255,
        description="Extra detail; required when 'other' is selected.",
    )


class MedicalHistorySection(BaseModel):
    """Medical History section of the survey."""

    model_config = ConfigDict(extra="forbid")

    conditions: list[MedicalConditionItem] = Field(
        min_length=1,
        max_length=MAX_CONDITIONS,
        description="At least one selection ('none' when there are no conditions).",
    )

    @model_validator(mode="after")
    def _validate_conditions(self) -> "MedicalHistorySection":
        """Reject contradictory or incomplete condition selections."""
        seen: set[MedicalConditionType] = set()
        for item in self.conditions:
            if item.condition is MedicalConditionType.other and not item.details:
                raise ValueError(
                    "condition 'other' requires the details field to describe it"
                )
            if item.condition in seen:
                raise ValueError(
                    f"condition '{item.condition.value}' was selected more than once"
                )
            seen.add(item.condition)
        if MedicalConditionType.none in seen and len(self.conditions) > 1:
            raise ValueError(
                "condition 'none' cannot be combined with other conditions"
            )
        return self


# --------------------------------------------------------------------------
# Step 3 - Current Symptoms
# --------------------------------------------------------------------------
class SymptomItem(BaseModel):
    """A single reported symptom."""

    model_config = ConfigDict(extra="forbid")

    symptom: LongText = Field(description="What the patient is experiencing.")
    duration: ShortText = Field(
        description="How long the symptom lasts, e.g. '3 days'."
    )
    severity: SymptomSeverity = Field(description="mild, moderate or severe.")
    notes: OptionalText = Field(default=None, max_length=500)


class CurrentSymptomsSection(BaseModel):
    """Current Symptoms section of the survey.

    An empty ``symptoms`` list means the patient reported no current symptoms.
    """

    model_config = ConfigDict(extra="forbid")

    symptoms: list[SymptomItem] = Field(
        default_factory=list, max_length=MAX_SYMPTOMS
    )


# --------------------------------------------------------------------------
# Step 4 - Medications
# --------------------------------------------------------------------------
class MedicationItem(BaseModel):
    """A medication the patient currently takes."""

    model_config = ConfigDict(extra="forbid")

    name: MediumText = Field(description="Medicine name.")
    dosage: ShortText = Field(description="Dosage, e.g. '500 mg'.")
    frequency: ShortText = Field(description="How often it is taken, e.g. 'twice daily'.")


class MedicationsSection(BaseModel):
    """Medications section of the survey."""

    model_config = ConfigDict(extra="forbid")

    medications: list[MedicationItem] = Field(
        default_factory=list, max_length=MAX_MEDICATIONS
    )


# --------------------------------------------------------------------------
# Step 5 - Allergies (+ optional additional information)
# --------------------------------------------------------------------------
class AllergyItem(BaseModel):
    """A known allergy."""

    model_config = ConfigDict(extra="forbid")

    allergen: MediumText = Field(description="Substance the patient is allergic to.")
    description: OptionalText = Field(
        default=None, max_length=500, description="Reaction / extra detail."
    )


class AllergiesSection(BaseModel):
    """Allergies section of the survey."""

    model_config = ConfigDict(extra="forbid")

    allergies: list[AllergyItem] = Field(
        default_factory=list, max_length=MAX_ALLERGIES
    )


# --------------------------------------------------------------------------
# Step 6 - Review & Submit
# --------------------------------------------------------------------------
class HealthAssessmentCreate(BaseModel):
    """Full survey payload used for submit (POST) and full update (PUT)."""

    model_config = ConfigDict(extra="forbid")

    basic_information: BasicInformation = Field(
        description="Step 1 - required."
    )
    medical_history: MedicalHistorySection = Field(
        description="Step 2 - required."
    )
    current_symptoms: CurrentSymptomsSection = Field(
        default_factory=CurrentSymptomsSection,
        description="Step 3 - optional; empty means no symptoms reported.",
    )
    medications: MedicationsSection = Field(
        default_factory=MedicationsSection, description="Step 4 - optional."
    )
    allergies: AllergiesSection = Field(
        default_factory=AllergiesSection, description="Step 5 - optional."
    )
    additional_information: OptionalText = Field(
        default=None,
        max_length=ADDITIONAL_INFORMATION_MAX_LENGTH,
        description="Optional free-text information the patient considers important.",
    )


class HealthAssessmentUpdate(BaseModel):
    """Partial survey payload used for PATCH updates.

    Only the sections present in the request body are replaced; omitted sections
    keep their stored values.  Sending ``null`` for ``additional_information``
    clears that field.
    """

    model_config = ConfigDict(extra="forbid")

    basic_information: BasicInformation | None = None
    medical_history: MedicalHistorySection | None = None
    current_symptoms: CurrentSymptomsSection | None = None
    medications: MedicationsSection | None = None
    allergies: AllergiesSection | None = None
    additional_information: OptionalText = Field(
        default=None, max_length=ADDITIONAL_INFORMATION_MAX_LENGTH
    )

    @model_validator(mode="after")
    def _require_at_least_one_section(self) -> "HealthAssessmentUpdate":
        """Reject empty PATCH bodies so the endpoint cannot be a no-op."""
        if not self.model_fields_set:
            raise ValueError(
                "provide at least one survey section to update"
            )
        return self


# --------------------------------------------------------------------------
# Read models
# --------------------------------------------------------------------------
class BasicInformationRead(BasicInformation):
    """Basic Information plus the derived BMI values.

    ``bmi`` and ``bmi_category`` are computed by the API from height and weight
    and are later consumed by the Risk agent.
    """

    bmi: float | None = None
    bmi_category: str | None = None


class HealthAssessmentRead(BaseModel):
    """Complete health assessment returned by the read endpoints."""

    id: int
    patient_id: int
    status: AssessmentStatus
    basic_information: BasicInformationRead
    medical_history: MedicalHistorySection
    current_symptoms: CurrentSymptomsSection
    medications: MedicationsSection
    allergies: AllergiesSection
    additional_information: str | None = None
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------
# Survey metadata - the single source of truth shared with the wizard UI
# --------------------------------------------------------------------------
class OptionItem(BaseModel):
    """A selectable survey option with a human readable label."""

    value: str
    label: str
    requires_details: bool = False


class SurveyStep(BaseModel):
    """One step of the multi-step survey UI."""

    step: int
    key: str
    title: str
    description: str
    required: bool


class NumericRange(BaseModel):
    """Inclusive numeric range applied to a survey field."""

    min: float
    max: float


class SurveyLimits(BaseModel):
    """Validation bounds advertised to the UI so it can pre-validate input."""

    age: NumericRange
    height_cm: NumericRange
    weight_kg: NumericRange
    additional_information_max_length: int
    max_conditions: int
    max_symptoms: int
    max_medications: int
    max_allergies: int


class SurveyOptions(BaseModel):
    """All controlled vocabularies used by the survey."""

    genders: list[OptionItem]
    medical_conditions: list[OptionItem]
    severities: list[OptionItem]


class SurveyMetadata(BaseModel):
    """Everything the frontend needs to render the onboarding survey."""

    title: str
    steps: list[SurveyStep]
    options: SurveyOptions
    limits: SurveyLimits