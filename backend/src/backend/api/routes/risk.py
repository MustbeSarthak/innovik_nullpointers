"""Patient-facing risk evaluation endpoint."""

from fastapi import APIRouter

from backend.agents.risk.models import RiskAssessment, RiskRequest
from backend.api.deps import CurrentPatient, DbSession
from backend.services.risk_service import evaluate_patient_risk

router = APIRouter(prefix="/risk", tags=["Risk Evaluation"])


@router.post("/evaluate", response_model=RiskAssessment, summary="Evaluate current health risks")
def evaluate_current_risk(
    request: RiskRequest, patient: CurrentPatient, db: DbSession
) -> RiskAssessment:
    """Return a grounded, patient-scoped risk assessment with safety guidance."""
    return evaluate_patient_risk(db, patient.id, request)
