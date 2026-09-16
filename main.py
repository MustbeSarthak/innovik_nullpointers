"""Convenience shim so ``uvicorn main:app`` works from the project root.

The real application factory lives in :mod:`backend.main`.
"""

from backend.main import app, create_app

__all__ = ["app", "create_app"]

