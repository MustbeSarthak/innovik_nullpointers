"""Non-blocking background timeout worker for unacknowledged alerts."""

import asyncio

from backend.core.config import get_settings
from backend.core.database import SessionLocal
from backend.alerts.service import AlertService


async def alert_timeout_worker(stop_event: asyncio.Event) -> None:
    """Poll alert deadlines without blocking FastAPI request handlers."""
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            AlertService().check_timeouts(db)
        finally:
            db.close()
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=min(max(get_settings().alert_ack_timeout_seconds / 10, 0.1), 5.0),
            )
        except asyncio.TimeoutError:
            pass
