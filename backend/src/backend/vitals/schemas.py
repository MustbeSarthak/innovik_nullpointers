"""API and service schemas for continuous vital readings."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from backend.vitals.reference_ranges import SexProfile, SimulationScenario, SimulationState


class VitalSource(str, Enum):
    simulator = "SIMULATED"
    manual = "MANUAL"
    device = "DEVICE"


class VitalReadingCreate(BaseModel):
    """Complete vital sample; missing values are rejected rather than invented."""

    timestamp: datetime | None = None
    heart_rate: float = Field(gt=0, le=300)
    systolic_bp: float = Field(gt=0, le=300)
    diastolic_bp: float = Field(gt=0, le=200)
    spo2: float = Field(gt=0, le=100)
    temperature: float = Field(gt=20, le=50)
    glucose: float = Field(gt=0, le=1000)
    source: VitalSource = VitalSource.manual
    simulator_state: SimulationState | None = None
    simulator_profile: SexProfile | None = None
    simulator_scenario: SimulationScenario | None = None


class VitalReadingRead(VitalReadingCreate):
    """Persisted vital sample."""

    model_config = ConfigDict(from_attributes=True)

    reading_id: int = Field(validation_alias="id")
    patient_id: int
    created_at: datetime


class VitalHistoryRead(BaseModel):
    items: list[VitalReadingRead]
    total: int
    limit: int
    offset: int


class SimulatorStartRequest(BaseModel):
    profile: SexProfile = SexProfile.male
    state: SimulationState = SimulationState.normal
    interval_seconds: float | None = Field(default=None, gt=0)
    scenario: SimulationScenario = SimulationScenario.normal


class SimulatorStatusRead(BaseModel):
    patient_id: int
    running: bool
    paused: bool
    profile: SexProfile | None
    state: SimulationState | None
    interval_seconds: float
    scenario: SimulationScenario | None


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alert_id: int = Field(validation_alias="id")
    patient_id: int
    status: str
    risk_score: int
    risk_level: str
    finding: str
    source: str
    created_at: datetime
    sms_sent_at: datetime | None
    acknowledged_at: datetime | None
    escalation_at: datetime | None
    hospital_result: str | None
