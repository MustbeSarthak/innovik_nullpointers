"""Alert creation, cooldown, acknowledgement, and escalation."""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.alerts.providers import HospitalProvider, MockHospitalProvider, MockSmsProvider, SmsProvider
from backend.core.config import get_settings
from backend.models.alert import Alert, AlertStatus
from backend.models.vital_reading import VitalReading
from backend.agents.risk.models import RiskAssessment, RiskLevel, RiskFinding


def _aware(value: datetime) -> datetime:
    """Treat SQLite's naive UTC timestamps as UTC for deadline comparisons."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class AlertService:
    """Apply risk actions without blocking request handlers."""

    def __init__(self, sms_provider: SmsProvider | None = None, hospital_provider: HospitalProvider | None = None) -> None:
        self.sms_provider = sms_provider or MockSmsProvider()
        self.hospital_provider = hospital_provider or MockHospitalProvider()

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
            self._send_sms(db, alert)
        db.commit()
        db.refresh(alert)
        return alert

    def _send_sms(self, db: Session, alert: Alert) -> None:
        recipient = get_settings().caretaker_phone_number
        if recipient:
            self.sms_provider.send(
                recipient,
                f"HIGH RISK ALERT for patient {alert.patient_id}: {alert.finding}. Please acknowledge promptly.",
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
