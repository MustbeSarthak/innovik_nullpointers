"""Survey metadata: steps, controlled vocabularies and validation limits.

Serving this from the API (instead of hard-coding it in the frontend) keeps the
wizard UI and the validation rules from drifting apart.
"""

from backend.models.enums import (
    Gender,
    MedicalConditionType,
    SymptomSeverity,
)
from backend.schemas.assessment import (
    NumericRange,
    OptionItem,
    SurveyLimits,
    SurveyMetadata,
    SurveyOptions,
    SurveyStep,
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
)

GENDER_LABELS: dict[Gender, str] = {
    Gender.male: "Male",
    Gender.female: "Female",
    Gender.other: "Other",
    Gender.prefer_not_to_say: "Prefer not to say",
}

CONDITION_LABELS: dict[MedicalConditionType, str] = {
    MedicalConditionType.diabetes: "Diabetes",
    MedicalConditionType.hypertension: "Hypertension (high blood pressure)",
    MedicalConditionType.asthma: "Asthma",
    MedicalConditionType.heart_related: "Heart-related condition",
    MedicalConditionType.kidney_related: "Kidney-related condition",
    MedicalConditionType.allergies: "Allergies",
    MedicalConditionType.other: "Other (please describe)",
    MedicalConditionType.none: "None of the above",
}

CONDITION_DESCRIPTIONS: dict[MedicalConditionType, str] = {
    MedicalConditionType.diabetes: "Blood sugar / glucose related condition.",
    MedicalConditionType.hypertension: "Persistently high blood pressure.",
    MedicalConditionType.asthma: "Airway / breathing condition.",
    MedicalConditionType.heart_related: "For example a cardiac condition or arrhythmia.",
    MedicalConditionType.kidney_related: "For example chronic kidney disease.",
    MedicalConditionType.allergies: "Diagnosed allergic condition.",
    MedicalConditionType.other: "Anything else diagnosed by a clinician.",
    MedicalConditionType.none: "Select this when no condition applies.",
}

SEVERITY_LABELS: dict[SymptomSeverity, str] = {
    SymptomSeverity.mild: "Mild - noticeable but not limiting",
    SymptomSeverity.moderate: "Moderate - affects daily activities",
    SymptomSeverity.severe: "Severe - significantly limiting",
}

SURVEY_STEPS: list[SurveyStep] = [
    SurveyStep(
        step=1,
        key="basic_information",
        title="Basic Information",
        description="Tell us the basics so we can personalise your care.",
        required=True,
    ),
    SurveyStep(
        step=2,
        key="medical_history",
        title="Medical History",
        description="Select any existing conditions, or choose 'None of the above'.",
        required=True,
    ),
    SurveyStep(
        step=3,
        key="current_symptoms",
        title="Current Symptoms",
        description="Share any symptoms you are experiencing right now.",
        required=False,
    ),
    SurveyStep(
        step=4,
        key="medications",
        title="Medications",
        description="List the medicines you currently take.",
        required=False,
    ),
    SurveyStep(
        step=5,
        key="allergies",
        title="Allergies",
        description="Note any known allergies and what happens when exposed.",
        required=False,
    ),
    SurveyStep(
        step=6,
        key="review",
        title="Review & Submit",
        description="Check your answers and add anything else that matters.",
        required=True,
    ),
]


def _condition_options() -> list[OptionItem]:
    """Build the medical-history options with labels and detail requirements."""
    return [
        OptionItem(
            value=condition.value,
            label=CONDITION_LABELS[condition],
            requires_details=condition is MedicalConditionType.other,
        )
        for condition in MedicalConditionType
    ]


def build_survey_metadata() -> SurveyMetadata:
    """Return the metadata that drives the multi-step survey UI."""
    return SurveyMetadata(
        title="Patient Health Assessment",
        steps=SURVEY_STEPS,
        options=SurveyOptions(
            genders=[
                OptionItem(value=gender.value, label=GENDER_LABELS[gender])
                for gender in Gender
            ],
            medical_conditions=_condition_options(),
            severities=[
                OptionItem(value=severity.value, label=SEVERITY_LABELS[severity])
                for severity in SymptomSeverity
            ],
        ),
        limits=SurveyLimits(
            age=NumericRange(min=AGE_MIN, max=AGE_MAX),
            height_cm=NumericRange(min=HEIGHT_MIN_CM, max=HEIGHT_MAX_CM),
            weight_kg=NumericRange(min=WEIGHT_MIN_KG, max=WEIGHT_MAX_KG),
            additional_information_max_length=ADDITIONAL_INFORMATION_MAX_LENGTH,
            max_conditions=MAX_CONDITIONS,
            max_symptoms=MAX_SYMPTOMS,
            max_medications=MAX_MEDICATIONS,
            max_allergies=MAX_ALLERGIES,
        ),
    )