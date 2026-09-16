"""Optional Acno AI intelligence provider.

No Acno SDK or official endpoint is present in this repository. The provider
therefore remains disabled unless an operator supplies an exact configured URL
and API key. Deterministic Module 5 safety evaluation remains authoritative.
"""

from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from backend.core.config import get_settings


class AcnoRiskAnalysis(BaseModel):
    """Validated provider output; never used without schema validation."""

    risk_level: str = "low"
    score: int = Field(ge=0, le=100)
    detected_indicators: list[str] = Field(default_factory=list)
    reason: str
    escalation_required: bool = False


class AcnoProvider(Protocol):
    """Provider contract for optional intelligence analysis."""

    def analyze(self, context: dict[str, Any]) -> AcnoRiskAnalysis | None: ...


class AcnoAIProvider:
    """Call an explicitly configured Acno-compatible endpoint.

    The implementation does not claim support for an undocumented Acno SDK or
    response contract. Without both configuration values it returns ``None``
    and the deterministic risk engine continues normally.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.acno_ai_api_key
        self.base_url = base_url or settings.acno_ai_base_url
        self.model = settings.acno_ai_model
        self.timeout = settings.acno_ai_timeout_seconds

    def analyze(self, context: dict[str, Any]) -> AcnoRiskAnalysis | None:
        if not self.api_key or not self.base_url:
            return None
        try:
            response = httpx.post(
                self.base_url,
                json={"model": self.model, "context": context},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return AcnoRiskAnalysis.model_validate(response.json())
        except (httpx.HTTPError, ValueError):
            return None


def build_acno_context(
    patient_id: int,
    assessment: Any | None,
    current_vitals: dict[str, Any],
    recent_vitals: list[dict[str, Any]],
    medical_context: Any,
) -> dict[str, Any]:
    """Build bounded, patient-scoped context without fabricating values."""
    return {
        "patient": {
            "id": patient_id,
            "age": assessment.basic_information.age if assessment else None,
            "gender": assessment.basic_information.gender.value if assessment else None,
        },
        "currentVitals": current_vitals,
        "recentVitals": recent_vitals,
        "trend": _trend(recent_vitals, current_vitals),
        "medicalHistory": [item.condition.value for item in assessment.medical_history.conditions] if assessment else [],
        "medications": [item.name for item in assessment.medications.medications] if assessment else [],
        "symptoms": [item.symptom for item in assessment.current_symptoms.symptoms] if assessment else [],
        "allergies": [item.allergen for item in assessment.allergies.allergies] if assessment else [],
        "retrievedContext": [item.model_dump() for item in medical_context.excerpts[:5]],
    }


def _trend(recent: list[dict[str, Any]], current: dict[str, Any]) -> dict[str, str]:
    if not recent:
        return {}
    result: dict[str, str] = {}
    previous = recent[-1]
    for name, value in current.items():
        old = previous.get(name)
        if isinstance(value, (int, float)) and isinstance(old, (int, float)):
            result[name] = "rising" if value > old else "falling" if value < old else "stable"
    return result