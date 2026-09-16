"""Alert creation, cooldown, acknowledgement, and escalation."""

import asyncio
import json
import logging
from threading import Thread
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.alerts.providers import (
    HospitalProvider,
    MockHospitalProvider,
    MockSmsProvider,
    SmsProvider,
    TwilioSmsProvider,
    WhatsAppProvider,
)
from backend.core.config import get_settings
from backend.models.alert import Alert, AlertStatus
from backend.models.patient import Patient
from backend.models.vital_reading import VitalReading
from backend.agents.risk.models import RiskAssessment, RiskLevel, RiskFinding


logger = logging.getLogger(__name__)


def _aware(value: datetime) -> datetime:
    """Treat SQLite's naive UTC timestamps as UTC for deadline comparisons."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class AlertService:
    """Apply risk actions without blocking request handlers."""

    def __init__(
        self,
        sms_provider: SmsProvider | None = None,
        hospital_provider: HospitalProvider | None = None,
        whatsapp_provider: WhatsAppProvider | None = None,
    ) -> None:
        self.sms_provider = sms_provider or self._default_sms_provider()
        self.hospital_provider = hospital_provider or MockHospitalProvider()
        self.whatsapp_provider = whatsapp_provider or WhatsAppProvider()

    @staticmethod
    def _default_sms_provider() -> SmsProvider:
        settings = get_settings()
        if settings.sms_provider.strip().lower() == "twilio":
            return TwilioSmsProvider()
        return MockSmsProvider()

    def process_reading(self, db: Session, reading: VitalReading, risk: RiskAssessment) -> Alert | None:
        if risk.score < 50:
            return None
        high = risk.score >= 70
        status = AlertStatus.CREATED if high else AlertStatus.SPECIAL_ATTENTION
        active_statuses = [
            AlertStatus.CREATED,
            AlertStatus.SMS_SENT,
            AlertStatus.WAITING_FOR_ACK,
        ] if high else [AlertStatus.SPECIAL_ATTENTION]
        existing = db.scalar(
            select(Alert).where(
                Alert.patient_id == reading.patient_id,
                Alert.status.in_(active_statuses),
                Alert.created_at >= datetime.now(timezone.utc) - timedelta(seconds=get_settings().alert_ack_timeout_seconds),
            ).order_by(desc(Alert.created_at))
        )
        if existing is not None:
            return existing
        finding = risk.findings[0].finding if risk.findings else "Vital monitoring risk signal requires attention."
        alert = Alert(
            patient_id=reading.patient_id,
            status=status,
            risk_score=risk.score,
            risk_level=risk.overall_risk.value,
            finding=finding,
            source=reading.source,
        )
        db.add(alert)
        db.flush()
        if high:
            self._notify_caretaker(db, alert, reading)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def _whatsapp_message(alert: Alert, reading: VitalReading, patient: Patient | None) -> str:
        """Build a concise, caregiver-facing high-risk monitoring message."""
        patient_name = patient.full_name if patient else "Patient"
        patient_phone = patient.phone_number if patient and patient.phone_number else "Not provided"
        finding = " ".join(alert.finding.split())[:600]
        alert_label = "Medication Alert" if "medication" in finding.lower() else "Vital Alert"
        vitals = (
            f"Heart rate: {reading.heart_rate:g} bpm; "
            f"Blood pressure: {reading.systolic_bp:g}/{reading.diastolic_bp:g} mmHg; "
            f"SpO2: {reading.spo2:g}%; Temperature: {reading.temperature:g} C; "
            f"Glucose: {reading.glucose:g} mg/dL"
        )
        return (
            "HEALTHCARE ALERT\n\n"
            f"Patient: {patient_name}\n"
            f"Patient phone: {patient_phone}\n"
            f"Risk level: {alert.risk_level.upper()}\n\n"
            f"{alert_label}:\n{finding}\n\n"
            f"Current vitals:\n{vitals}\n\n"
            "Please check the patient immediately."
        )

    def _queue_whatsapp_notification(self, recipient: str, message: str) -> None:
        """Schedule delivery without delaying a vital-reading request or simulator."""
        async def deliver() -> None:
            try:
                await self.whatsapp_provider.send_message(recipient, message)
            except Exception:  # Provider implementations must never break escalation.
                logger.exception("Unexpected WhatsApp provider failure; alert escalation continues.")

        def run_in_thread() -> None:
            asyncio.run(deliver())

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            Thread(target=run_in_thread, name="caretaker-whatsapp", daemon=True).start()
        else:
            task = loop.create_task(deliver())
            # Retrieving the exception keeps a custom provider from producing an
            # unobserved-task warning while retaining the original alert flow.
            task.add_done_callback(lambda completed: completed.exception() if not completed.cancelled() else None)

    def _notify_caretaker(self, db: Session, alert: Alert, reading: VitalReading) -> None:
        recipient = get_settings().caretaker_phone_number
        patient = db.get(Patient, alert.patient_id)
        if not recipient:
            logger.error(
                "Critical alert %s was created but no caretaker recipient is configured; "
                "set CARETAKER_PHONE_NUMBER.",
                alert.id,
            )
        else:
            try:
                self.sms_provider.send(
                    recipient,
                    f"HIGH RISK ALERT for patient {alert.patient_id}: {alert.finding}. Please acknowledge promptly.",
                )
            except Exception:
                logger.exception("Caretaker SMS delivery failed for alert %s.", alert.id)
            self._queue_whatsapp_notification(
                recipient,
                self._whatsapp_message(alert, reading, patient),
            )
        alert.sms_sent_at = datetime.now(timezone.utc)
        alert.status = AlertStatus.WAITING_FOR_ACK

    def acknowledge(self, db: Session, patient_id: int, alert_id: int) -> Alert:
        alert = db.scalar(select(Alert).where(Alert.id == alert_id, Alert.patient_id == patient_id))
        if alert is None:
            raise LookupError("alert was not found for this patient")
        if alert.status is AlertStatus.ACKNOWLEDGED:
            return alert
        if alert.status is not AlertStatus.WAITING_FOR_ACK:
            return alert
        now = datetime.now(timezone.utc)
        if alert.sms_sent_at and now - _aware(alert.sms_sent_at) > timedelta(seconds=get_settings().alert_ack_timeout_seconds):
            self.escalate(db, alert)
            return alert
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = now
        db.commit()
        db.refresh(alert)
        return alert

    def escalate(self, db: Session, alert: Alert) -> Alert:
        if alert.status is AlertStatus.ACKNOWLEDGED:
            return alert
        hospitals = self.hospital_provider.nearest()
        alert.status = AlertStatus.HOSPITAL_SEARCH_TRIGGERED if hospitals else AlertStatus.NO_RESPONSE
        alert.escalation_at = datetime.now(timezone.utc)
        alert.hospital_result = json.dumps([item.__dict__ for item in hospitals]) if hospitals else None
        db.commit()
        db.refresh(alert)
        return alert

    def check_timeouts(self, db: Session) -> list[Alert]:
        """Escalate expired unacknowledged alerts; intended for a scheduler."""
        alerts = list(db.scalars(select(Alert).where(Alert.status == AlertStatus.WAITING_FOR_ACK)))
        now = datetime.now(timezone.utc)
        changed = []
        for alert in alerts:
            if alert.sms_sent_at and now - _aware(alert.sms_sent_at) >= timedelta(seconds=get_settings().alert_ack_timeout_seconds):
                changed.append(self.escalate(db, alert))
        return changed


def process_reading(db: Session, reading: VitalReading, risk: RiskAssessment | None = None) -> Alert | None:
    """Pipeline hook; callers provide risk output from the existing graph."""
    if risk is None:
        return None
    return AlertService().process_reading(db, reading, risk)
