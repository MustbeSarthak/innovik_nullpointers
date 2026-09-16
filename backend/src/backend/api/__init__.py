"""API layer: dependencies, routers and HTTP error handling."""

from backend.api.deps import get_current_patient, get_db

__all__ = ["get_current_patient", "get_db"]