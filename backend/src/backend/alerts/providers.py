"""Pluggable caretaker-notification and hospital providers."""

from dataclasses import dataclass
import logging

import httpx

from backend.core.config import get_settings


logger = logging.getLogger(__name__)
GRAPH_API_BASE_URL = "https://graph.facebook.com"
TWILIO_API_BASE_URL = "https://api.twilio.com"
_PHONE_CHARACTERS = frozenset("0123456789 +-()")


def normalize_whatsapp_phone_number(phone_number: str) -> str | None:
    """Return a Meta-compatible international number without punctuation.

    Indian mobile numbers stored locally with no country code are converted to
    ``91`` + the ten-digit mobile number.  Existing international numbers are
    preserved (apart from formatting), so the helper remains suitable for
    caretakers outside India as well.
    """
    candidate = phone_number.strip()
    if not candidate or not set(candidate) <= _PHONE_CHARACTERS:
        return None

    digits = "".join(character for character in candidate if character.isdigit())
    # ``00`` is a common international-dialling prefix, but Meta expects the
    # country code directly (the same format used without a leading ``+``).
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits or len(digits) > 15:
        return None

    # Indian mobile numbers have ten digits and conventionally begin 6-9.  A
    # 12-digit 91-prefixed value is already in the format Meta expects.
    if len(digits) == 10 and digits[0] in "6789":
        return f"91{digits}"
    return digits


@dataclass(frozen=True)
class SmsMessage:
    recipient: str
    message: str


class SmsProvider:
    """Provider interface for caretaker notifications."""

    def send(self, recipient: str, message: str) -> SmsMessage:
        raise NotImplementedError


class MockSmsProvider(SmsProvider):
    """Record messages in memory for development and tests."""

    def __init__(self) -> None:
        self.messages: list[SmsMessage] = []

    def send(self, recipient: str, message: str) -> SmsMessage:
        item = SmsMessage(recipient, message)
        self.messages.append(item)
        return item


class TwilioSmsProvider(SmsProvider):
    """Send caretaker SMS messages through the Twilio Messages API."""

    def __init__(
        self,
        *,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_phone_number: str | None = None,
        timeout_seconds: float | None = None,
        api_base_url: str = TWILIO_API_BASE_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.account_sid = account_sid if account_sid is not None else settings.twilio_account_sid
        self.auth_token = auth_token if auth_token is not None else settings.twilio_auth_token
        self.from_phone_number = (
            from_phone_number
            if from_phone_number is not None
            else settings.twilio_from_phone_number
        )
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.twilio_timeout_seconds
        )
        self.api_base_url = api_base_url.rstrip("/")
        self._transport = transport

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_phone_number)

    def send(self, recipient: str, message: str) -> SmsMessage:
        """Send one SMS, raising a useful error when Twilio rejects it."""
        if not self.is_configured:
            raise RuntimeError(
                "Twilio SMS is not configured; set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_FROM_PHONE_NUMBER"
            )

        normalized_recipient = normalize_whatsapp_phone_number(recipient)
        normalized_sender = normalize_whatsapp_phone_number(self.from_phone_number or "")
        if not normalized_recipient or not normalized_sender:
            raise ValueError("Twilio SMS requires valid international phone numbers")

        endpoint = (
            f"{self.api_base_url}/2010-04-01/Accounts/"
            f"{self.account_sid}/Messages.json"
        )
        client_options: dict[str, object] = {"timeout": self.timeout_seconds}
        if self._transport is not None:
            client_options["transport"] = self._transport
        with httpx.Client(**client_options) as client:
            response = client.post(
                endpoint,
                auth=(self.account_sid, self.auth_token),
                data={
                    "To": f"+{normalized_recipient}",
                    "From": f"+{normalized_sender}",
                    "Body": message,
                },
            )
            response.raise_for_status()

        return SmsMessage(recipient, message)


class WhatsAppProvider:
    """Async Meta WhatsApp Cloud API provider for caretaker alerts.

    Credentials are intentionally optional: a local or test deployment can run
    the established :class:`MockSmsProvider` flow without a Meta account.
    ``True`` means Meta accepted the request, not that the recipient has read it.
    """

    def __init__(
        self,
        *,
        access_token: str | None = None,
        phone_number_id: str | None = None,
        api_version: str | None = None,
        timeout_seconds: float | None = None,
        api_base_url: str = GRAPH_API_BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.access_token = access_token if access_token is not None else settings.whatsapp_access_token
        self.phone_number_id = phone_number_id if phone_number_id is not None else settings.whatsapp_phone_number_id
        self.api_version = api_version if api_version is not None else settings.whatsapp_api_version
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.whatsapp_timeout_seconds
        self.api_base_url = api_base_url.rstrip("/")
        self._transport = transport

    @property
    def is_configured(self) -> bool:
        """Whether the minimum safe Meta credentials are available."""
        return bool(self.access_token and self.phone_number_id and self.api_version)

    @property
    def missing_configuration(self) -> tuple[str, ...]:
        """Return the Meta settings that prevent real delivery."""
        missing = []
        if not self.access_token:
            missing.append("WHATSAPP_ACCESS_TOKEN")
        if not self.phone_number_id:
            missing.append("WHATSAPP_PHONE_NUMBER_ID")
        if not self.api_version:
            missing.append("WHATSAPP_API_VERSION")
        return tuple(missing)

    async def send_message(self, phone_number: str, message: str) -> bool:
        """Submit one text message to Meta, returning ``False`` on any failure."""
        if not self.is_configured:
            logger.error(
                "WhatsApp caretaker notification was not sent; missing configuration: %s",
                ", ".join(self.missing_configuration),
            )
            return False

        recipient = normalize_whatsapp_phone_number(phone_number)
        if recipient is None:
            logger.warning("Skipping WhatsApp notification because caretaker phone number is invalid.")
            return False

        api_version = self.api_version.strip("/")
        phone_number_id = self.phone_number_id.strip("/")
        if not api_version or not phone_number_id:
            logger.warning("Skipping WhatsApp notification because Meta configuration is invalid.")
            return False

        endpoint = f"{self.api_base_url}/{api_version}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message},
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        client_options: dict[str, object] = {"timeout": self.timeout_seconds}
        if self._transport is not None:
            client_options["transport"] = self._transport
        try:
            async with httpx.AsyncClient(**client_options) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                response_body = response.json()
        except httpx.TimeoutException:
            logger.warning("WhatsApp notification timed out; caretaker notification was not sent.")
            return False
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "WhatsApp notification was rejected by Meta (status %s).",
                exc.response.status_code,
            )
            return False
        except httpx.HTTPError:
            logger.exception("WhatsApp notification failed while calling Meta.")
            return False
        except ValueError:
            logger.warning("WhatsApp notification received an invalid Meta response.")
            return False

        messages = response_body.get("messages") if isinstance(response_body, dict) else None
        if (
            not isinstance(messages, list)
            or not messages
            or not isinstance(messages[0], dict)
            or not messages[0].get("id")
        ):
            logger.warning("WhatsApp notification received an unexpected Meta response.")
            return False
        return True


@dataclass(frozen=True)
class Hospital:
    name: str
    rating: float
    distance_km: float | None = None
    address: str | None = None
    contact: str | None = None


class HospitalProvider:
    """Provider interface; no live result is fabricated by the base system."""

    def nearest(self, *, latitude: float | None = None, longitude: float | None = None) -> list[Hospital]:
        raise NotImplementedError


class MockHospitalProvider(HospitalProvider):
    """Test provider that returns only explicitly configured hospitals."""

    def __init__(self, hospitals: list[Hospital] | None = None) -> None:
        self.hospitals = hospitals or []

    def nearest(self, *, latitude: float | None = None, longitude: float | None = None) -> list[Hospital]:
        return sorted(
            [item for item in self.hospitals if item.rating >= 4.0],
            key=lambda item: item.distance_km if item.distance_km is not None else float("inf"),
        )
