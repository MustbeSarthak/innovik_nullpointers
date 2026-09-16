"""Non-blocking per-patient vital simulator."""

import asyncio
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.services.vital_service import process_reading_risk, store_reading
from backend.vitals.reference_ranges import (
    SexProfile,
    SimulationScenario,
    SimulationState,
    get_reference_ranges,
    screening_ranges,
)
from backend.vitals.schemas import VitalReadingCreate, VitalSource


@dataclass
class SimulatorSession:
    patient_id: int
    profile: SexProfile
    state: SimulationState
    interval_seconds: float
    scenario: SimulationScenario = SimulationScenario.normal
    task: asyncio.Task | None = None
    paused: bool = False
    step: int = 0


class VitalSimulator:
    """Manage independent asyncio tasks; no request handler blocks or sleeps."""

    def __init__(self) -> None:
        self._sessions: dict[int, SimulatorSession] = {}

    def status(self, patient_id: int) -> SimulatorSession | None:
        return self._sessions.get(patient_id)

    async def start(self, patient_id: int, profile: SexProfile, state: SimulationState, interval_seconds: float, session_factory, scenario: SimulationScenario = SimulationScenario.normal) -> SimulatorSession:
        await self.stop(patient_id)
        session = SimulatorSession(patient_id, profile, state, interval_seconds, scenario)
        self._sessions[patient_id] = session
        session.task = asyncio.create_task(self._run(session, session_factory))
        return session

    async def stop(self, patient_id: int) -> None:
        session = self._sessions.pop(patient_id, None)
        if session and session.task:
            session.task.cancel()
            try:
                await session.task
            except asyncio.CancelledError:
                pass

    def pause(self, patient_id: int) -> SimulatorSession:
        session = self._sessions[patient_id]
        session.paused = True
        return session

    def resume(self, patient_id: int) -> SimulatorSession:
        session = self._sessions[patient_id]
        session.paused = False
        return session

    def set_state(self, patient_id: int, state: SimulationState) -> SimulatorSession:
        session = self._sessions[patient_id]
        session.state = state
        return session

    async def _run(self, session: SimulatorSession, session_factory) -> None:
        while True:
            # Give callers a chance to pause or stop a newly-created session
            # before its first sample is persisted.
            await asyncio.sleep(session.interval_seconds)
            if not session.paused:
                db: Session = session_factory()
                try:
                    payload = generate_demo_reading(
                        session.profile, session.state, session.step, session.scenario
                    )
                    reading = store_reading(db, session.patient_id, payload)
                    process_reading_risk(db, reading)
                    session.step += 1
                finally:
                    db.close()
            await asyncio.sleep(session.interval_seconds)


def generate_demo_reading(
    profile: SexProfile,
    state: SimulationState,
    step: int = 0,
    scenario: SimulationScenario = SimulationScenario.normal,
) -> VitalReadingCreate:
    """Generate a smooth, deterministic scenario reading for demo purposes."""
    scenario = SimulationScenario(scenario)
    normal = get_reference_ranges(profile)
    if scenario is SimulationScenario.normal:
        bands = screening_ranges(profile, state)
        values = {}
        for index, (name, (low, high)) in enumerate(bands.items()):
            wave = (math.sin((step + index) / 2) + 1) / 2
            values[name] = round(low + (high - low) * wave, 2)
    else:
        deterioration = screening_ranges(profile, SimulationState.critical)
        phase = min(step, 10) / 10
        if scenario is SimulationScenario.recovery:
            phase = 1.0 - phase
        if scenario is SimulationScenario.acute_event:
            phase = 0.0 if step == 0 else 1.0
        acute_targets = {
            "heart_rate": 135.0,
            "systolic_bp": 85.0,
            "diastolic_bp": 55.0,
            "spo2": 87.0,
            "temperature": 39.0,
            "glucose": 250.0,
        }
        values = {}
        for index, name in enumerate(normal):
            baseline = normal[name].midpoint()
            if scenario is SimulationScenario.acute_event:
                target = acute_targets[name]
            else:
                target_low, target_high = deterioration[name]
                target = (target_low + target_high) / 2
            wave = math.sin((step + index) / 2) * (normal[name].high - normal[name].low) * 0.04
            values[name] = round(baseline + (target - baseline) * phase + wave, 2)
    return VitalReadingCreate(
        timestamp=datetime.now(timezone.utc), source=VitalSource.simulator,
        simulator_state=state, simulator_profile=profile,
        simulator_scenario=scenario, **values
    )


simulator = VitalSimulator()
