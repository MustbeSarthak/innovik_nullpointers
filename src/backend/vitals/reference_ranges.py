"""Configurable demo screening ranges for simulated vitals.

These ranges are for demonstration and screening only, not diagnosis or
clinical decision-making.
"""

from dataclasses import dataclass
from enum import Enum


class SexProfile(str, Enum):
    male = "male"
    female = "female"


class SimulationState(str, Enum):
    normal = "normal"
    medium = "medium"
    critical = "critical"


class SimulationScenario(str, Enum):
    """Deterministic demo trajectories for continuous monitoring."""

    normal = "NORMAL"
    gradual_deterioration = "GRADUAL_DETERIORATION"
    acute_event = "ACUTE_EVENT"
    recovery = "RECOVERY"


@dataclass(frozen=True)
class VitalRange:
    low: float
    high: float
    unit: str

    def midpoint(self) -> float:
        return (self.low + self.high) / 2


DEMO_RANGES: dict[SexProfile, dict[str, VitalRange]] = {
    SexProfile.male: {
        "heart_rate": VitalRange(60, 100, "bpm"),
        "systolic_bp": VitalRange(90, 130, "mmHg"),
        "diastolic_bp": VitalRange(60, 85, "mmHg"),
        "spo2": VitalRange(95, 100, "%"),
        "temperature": VitalRange(36.1, 37.5, "C"),
        "glucose": VitalRange(70, 140, "mg/dL"),
    },
    SexProfile.female: {
        "heart_rate": VitalRange(60, 100, "bpm"),
        "systolic_bp": VitalRange(90, 130, "mmHg"),
        "diastolic_bp": VitalRange(60, 85, "mmHg"),
        "spo2": VitalRange(95, 100, "%"),
        "temperature": VitalRange(36.1, 37.5, "C"),
        "glucose": VitalRange(70, 140, "mg/dL"),
    },
}


def get_reference_ranges(profile: SexProfile) -> dict[str, VitalRange]:
    """Return a copy of the configured demo screening profile."""
    return dict(DEMO_RANGES[SexProfile(profile)])


def screening_ranges(profile: SexProfile, state: SimulationState) -> dict[str, tuple[float, float]]:
    """Return plausible generation bands for a demo state."""
    base = get_reference_ranges(profile)
    if state is SimulationState.normal:
        return {name: (item.low, item.high) for name, item in base.items()}
    if state is SimulationState.medium:
        return {
            "heart_rate": (101, 120), "systolic_bp": (131, 155),
            "diastolic_bp": (86, 100), "spo2": (91, 94),
            "temperature": (37.6, 39.0), "glucose": (141, 220),
        }
    return {
        "heart_rate": (121, 150), "systolic_bp": (156, 190),
        "diastolic_bp": (101, 120), "spo2": (85, 90),
        "temperature": (39.1, 40.5), "glucose": (221, 350),
    }
