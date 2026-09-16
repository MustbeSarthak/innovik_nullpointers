"""Authenticated continuous vital-monitoring endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from backend.api.deps import CurrentPatient, DbSession
from backend.core.config import get_settings
from backend.services.vital_service import (
    history_readings,
    latest_reading,
    process_reading_risk,
    store_reading,
)
from backend.vitals.schemas import (
    SimulatorStartRequest,
    SimulatorStatusRead,
    VitalHistoryRead,
    VitalReadingCreate,
    VitalReadingRead,
)
from backend.vitals.simulator import simulator
from backend.core.database import SessionLocal

router = APIRouter(prefix="/vitals", tags=["Vital Monitoring"])


def _status(patient_id: int) -> SimulatorStatusRead:
    session = simulator.status(patient_id)
    if session is None:
        return SimulatorStatusRead(
            patient_id=patient_id,
            running=False,
            paused=False,
            profile=None,
            state=None,
            interval_seconds=get_settings().vital_simulator_interval_seconds,
            scenario=None,
        )
    return SimulatorStatusRead(
        patient_id=patient_id,
        running=session.task is not None and not session.task.done(),
        paused=session.paused,
        profile=session.profile,
        state=session.state,
        interval_seconds=session.interval_seconds,
        scenario=session.scenario,
    )


@router.post("", response_model=VitalReadingRead, status_code=status.HTTP_201_CREATED)
def create_vital_reading(
    payload: VitalReadingCreate, patient: CurrentPatient, db: DbSession
) -> VitalReadingRead:
    """Store a complete patient-owned reading and evaluate its risk."""
    reading = store_reading(db, patient.id, payload)
    process_reading_risk(db, reading)
    return VitalReadingRead.model_validate(reading)


@router.get("/latest", response_model=VitalReadingRead | None)
def get_latest_vitals(patient: CurrentPatient, db: DbSession):
    """Return the latest reading belonging to the authenticated patient."""
    reading = latest_reading(db, patient.id)
    return VitalReadingRead.model_validate(reading) if reading else None


@router.get("/history", response_model=VitalHistoryRead)
def get_vital_history(
    patient: CurrentPatient,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> VitalHistoryRead:
    """Return bounded newest-first history for the authenticated patient."""
    return history_readings(db, patient.id, limit=limit, offset=offset)


@router.post("/simulator/start", response_model=SimulatorStatusRead)
async def start_vital_simulator(
    payload: SimulatorStartRequest, patient: CurrentPatient
) -> SimulatorStatusRead:
    """Start or restart the non-blocking simulator for this patient."""
    session = await simulator.start(
        patient.id,
        payload.profile,
        payload.state,
        payload.interval_seconds or get_settings().vital_simulator_interval_seconds,
        SessionLocal,
        payload.scenario,
    )
    return _status(session.patient_id)


@router.post("/simulator/stop", response_model=SimulatorStatusRead)
async def stop_vital_simulator(patient: CurrentPatient) -> SimulatorStatusRead:
    """Stop this patient's simulator without affecting other patients."""
    await simulator.stop(patient.id)
    return _status(patient.id)


@router.post("/simulator/pause", response_model=SimulatorStatusRead)
def pause_vital_simulator(patient: CurrentPatient) -> SimulatorStatusRead:
    """Pause this patient's simulator."""
    simulator.pause(patient.id)
    return _status(patient.id)


@router.post("/simulator/resume", response_model=SimulatorStatusRead)
def resume_vital_simulator(patient: CurrentPatient) -> SimulatorStatusRead:
    """Resume this patient's simulator."""
    simulator.resume(patient.id)
    return _status(patient.id)


@router.get("/simulator/status", response_model=SimulatorStatusRead)
def get_simulator_status(patient: CurrentPatient) -> SimulatorStatusRead:
    """Return only this patient's simulator state."""
    return _status(patient.id)
