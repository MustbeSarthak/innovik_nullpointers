"""Meta WhatsApp Cloud API notification tests without external requests."""

import asyncio
import json
from threading import Event
from urllib.parse import parse_qs

import httpx
import pytest

from backend.alerts.providers import (
    MockSmsProvider,
    TwilioSmsProvider,
    WhatsAppProvider,
    normalize_whatsapp_phone_number,
)
from backend.alerts.service import AlertService
from backend.agents.risk.models import RiskAssessment, RiskLevel
from backend.core.config import get_settings
from backend.services.vital_service import store_reading
from backend.vitals.schemas import VitalReadingCreate


def _high_risk(patient_id: int) -> RiskAssessment:
    return RiskAssessment(
        patient_id=patient_id,
        overall_risk=RiskLevel.critical,
        score=85,
        findings=[],
        evidence=[],
        uncertainties=[],
        recommended_action="Seek prompt professional care.",
    )


def _reading_payload() -> VitalReadingCreate:
    return VitalReadingCreate(
        heart_rate=132,
        systolic_bp=160,
        diastolic_bp=100,
        spo2=88,
        temperature=38.9,
        glucose=220,
    )


def test_whatsapp_provider_posts_normalized_payload_and_authorization_header() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"messages": [{"id": "wamid.test"}]})

    provider = WhatsAppProvider(
        access_token="test-token",
        phone_number_id="phone-number-id",
        api_version="v99.0",
        transport=httpx.MockTransport(handler),
    )

    sent = asyncio.run(provider.send_message("9876543210", "Please check immediately."))

    assert sent is True
    assert captured["url"] == "https://graph.facebook.com/v99.0/phone-number-id/messages"
    assert captured["headers"]["authorization"] == "Bearer test-token"  # type: ignore[index]
    assert captured["headers"]["content-type"] == "application/json"  # type: ignore[index]
    assert captured["payload"] == {
        "messaging_product": "whatsapp",
        "to": "919876543210",
        "type": "text",
        "text": {"body": "Please check immediately."},
    }


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (lambda request: httpx.Response(500, json={"error": {"message": "unavailable"}}), False),
        (lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("timed out", request=request)), False),
        (lambda request: httpx.Response(200, json={"messages": [{}]}), False),
    ],
)
def test_whatsapp_provider_handles_failures_gracefully(handler, expected: bool) -> None:
    provider = WhatsAppProvider(
        access_token="test-token",
        phone_number_id="phone-number-id",
        api_version="v99.0",
        transport=httpx.MockTransport(handler),
    )

    assert asyncio.run(provider.send_message("+919876543210", "Alert")) is expected


def test_whatsapp_provider_without_credentials_skips_delivery() -> None:
    provider = WhatsAppProvider(access_token="", phone_number_id="")

    assert asyncio.run(provider.send_message("+919876543210", "Alert")) is False
    assert provider.is_configured is False


def test_twilio_sms_provider_posts_message_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["payload"] = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        return httpx.Response(201, json={"sid": "SM123"})

    provider = TwilioSmsProvider(
        account_sid="AC123",
        auth_token="secret",
        from_phone_number="+15550001111",
        api_base_url="https://twilio.test",
        transport=httpx.MockTransport(handler),
    )

    sent = provider.send("9876543210", "Critical health alert.")

    assert sent.recipient == "9876543210"
    assert captured["url"] == "https://twilio.test/2010-04-01/Accounts/AC123/Messages.json"
    assert captured["auth"] == "Basic QUMxMjM6c2VjcmV0"
    assert captured["payload"] == {
        "To": "+919876543210",
        "From": "+15550001111",
        "Body": "Critical health alert.",
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9876543210", "919876543210"),
        ("+91 98765-43210", "919876543210"),
        ("919876543210", "919876543210"),
        ("+1 (555) 000-1234", "15550001234"),
        ("not-a-phone", None),
    ],
)
def test_phone_number_normalization(raw: str, expected: str | None) -> None:
    assert normalize_whatsapp_phone_number(raw) == expected


def test_high_risk_alert_queues_whatsapp_and_preserves_mock_sms(db, db_patient, monkeypatch) -> None:
    class RecordingWhatsAppProvider:
        def __init__(self) -> None:
            self.messages: list[tuple[str, str]] = []
            self.delivered = Event()

        async def send_message(self, phone_number: str, message: str) -> bool:
            self.messages.append((phone_number, message))
            self.delivered.set()
            return True

    settings = get_settings()
    monkeypatch.setattr(settings, "caretaker_phone_number", "9876543210")
    sms = MockSmsProvider()
    whatsapp = RecordingWhatsAppProvider()
    service = AlertService(sms_provider=sms, whatsapp_provider=whatsapp)  # type: ignore[arg-type]
    reading = store_reading(db, db_patient.id, _reading_payload())

    alert = service.process_reading(db, reading, _high_risk(db_patient.id))

    assert alert is not None
    assert len(sms.messages) == 1
    assert whatsapp.delivered.wait(timeout=1)
    assert service.process_reading(db, reading, _high_risk(db_patient.id)).id == alert.id
    assert len(whatsapp.messages) == 1
    recipient, message = whatsapp.messages[0]
    assert recipient == "9876543210"
    assert "Patient: Service Level Patient" in message
    assert "Risk level: CRITICAL" in message
    assert "Patient phone: Not provided" in message
    assert "Heart rate: 132 bpm" in message
