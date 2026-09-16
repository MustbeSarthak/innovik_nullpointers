"""Risk evaluation service integration with normalized patient assessment data."""

from sqlalchemy.orm import Session

from backend.agents.risk.models import RiskAssessment, RiskRequest
from backend.agents.risk.orchestrator import RiskEvaluationAgent
from backend.agents.risk.state import VitalReading
from backend.core.exceptions import AssessmentNotFoundError
from backend.services.assessment_service import require_assessment, to_read_model


def evaluate_patient_risk(
    db: Session,
    patient_id: int,
    request: RiskRequest,
    *,
    agent: RiskEvaluationAgent | None = None,
) -> RiskAssessment:
    """Evaluate one authenticated patient's current health context."""
    assessment = require_assessment(db, patient_id)
    return (agent or RiskEvaluationAgent()).evaluate(
        patient_id,
        assessment=to_read_model(assessment),
        query=request.query,
        vitals=[VitalReading.model_validate(item) for item in request.vitals],
    )
