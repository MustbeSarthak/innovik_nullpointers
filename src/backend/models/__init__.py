"""ORM models.

Importing this package registers every table on ``Base.metadata``; other
modules must import it (directly or through ``backend.core.database.init_db``)
before running ``create_all``.
"""

from backend.models.enums import (
    AssessmentStatus,
    Gender,
    MedicalConditionType,
    SymptomSeverity,
)
from backend.models.health_assessment import (
    Allergy,
    CurrentSymptoms,
    HealthAssessment,
    Medication,
    MedicalCondition,
)
from backend.models.patient import Patient
from backend.models.patient_document import (
    DocumentStatus,
    DocumentType,
    PatientDocument,
)
from backend.models.vital_reading import VitalReading
from backend.models.alert import Alert, AlertStatus
from backend.models.risk_assessment import PatientRiskAssessment

__all__ = [
    "Allergy",
    "AssessmentStatus",
    "CurrentSymptoms",
    "DocumentStatus",
    "DocumentType",
    "Gender",
    "HealthAssessment",
    "MedicalCondition",
    "MedicalConditionType",
    "Medication",
    "Patient",
    "PatientDocument",
    "VitalReading",
    "Alert",
    "AlertStatus",
    "PatientRiskAssessment",
    "SymptomSeverity",
]
