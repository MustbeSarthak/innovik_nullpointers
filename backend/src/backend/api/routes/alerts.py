"""Authenticated alert acknowledgement endpoints."""

from fastapi import APIRouter, HTTPException, status

from backend.alerts.service import AlertService
from backend.api.deps import CurrentPatient, DbSession
from backend.vitals.schemas import AlertRead

router = APIRouter(prefix="/alerts", tags=["Risk Alerts"])


@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge_alert(
    alert_id: int, patient: CurrentPatient, db: DbSession
) -> AlertRead:
    """Acknowledge an awaiting alert owned by the authenticated patient."""
    try:
        alert = AlertService().acknowledge(db, patient.id, alert_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AlertRead.model_validate(alert)
