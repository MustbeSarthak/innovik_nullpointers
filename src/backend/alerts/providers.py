"""Pluggable SMS and hospital providers with safe demo implementations."""

from dataclasses import dataclass


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
