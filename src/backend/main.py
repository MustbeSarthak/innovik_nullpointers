"""FastAPI application factory for the Healthcare Assistant backend.

Module 1 exposes the patient health assessment (survey) API.  Later modules plug
their routers, agents and MCP servers in here without touching existing code.
"""

from contextlib import asynccontextmanager
import asyncio
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import (
    alerts_router,
    auth_router,
    documents_router,
    health_assessment_router,
    risk_router,
    vitals_router,
)
from backend.alerts.scheduler import alert_timeout_worker
from backend.core.config import settings
from backend.core.database import init_db
from backend.core.exceptions import (
    AssessmentAlreadyExistsError,
    AssessmentNotFoundError,
    DocumentNotFoundError,
    DocumentTooLargeError,
    HealthcareAssistantError,
    PatientAlreadyExistsError,
    PatientNotFoundError,
)

DESCRIPTION = """
Backend for the Healthcare Assistant.

**Module 1 — Patient Health Assessment / Survey**

* a patient registers once and owns a single ``patient_id``
* the survey is stored in normalised tables linked to that ``patient_id``
* the answers are exposed to the future Memory, Risk, Monitoring and Response
  agents through the service layer and the MCP tools
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the database schema on start-up when enabled."""
    if settings.auto_create_tables:
        init_db()
    stop_event = asyncio.Event()
    timeout_task = asyncio.create_task(alert_timeout_worker(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        timeout_task.cancel()
        try:
            await timeout_task
        except asyncio.CancelledError:
            pass


def _validation_error_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Flatten pydantic validation errors into a client-friendly list."""
    details: list[dict[str, Any]] = []
    for error in exc.errors():
        location = [
            str(part)
            for part in error.get("loc", ())
            if part not in ("body", "query", "path")
        ]
        details.append(
            {
                "field": ".".join(location) or "body",
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
        )
    return details


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain exceptions onto consistent HTTP error responses."""

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            # 422 is spelled literally: the ``HTTP_422_UNPROCESSABLE_ENTITY``
            # constant is deprecated in newer Starlette releases.
            status_code=422,
            content={
                "detail": "Validation failed for the submitted health assessment",
                "errors": _validation_error_details(exc),
            },
        )

    @app.exception_handler(PatientAlreadyExistsError)
    async def _handle_patient_exists(
        request: Request, exc: PatientAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)}
        )

    @app.exception_handler(AssessmentAlreadyExistsError)
    async def _handle_assessment_exists(
        request: Request, exc: AssessmentAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": str(exc),
                "hint": "Use PUT or PATCH /api/v1/assessments/me to update the "
                "existing health assessment.",
            },
        )

    @app.exception_handler(AssessmentNotFoundError)
    async def _handle_assessment_missing(
        request: Request, exc: AssessmentNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": str(exc),
                "hint": "Submit the survey with POST /api/v1/assessments first.",
            },
        )

    @app.exception_handler(PatientNotFoundError)
    async def _handle_patient_missing(
        request: Request, exc: PatientNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
        )

    @app.exception_handler(DocumentNotFoundError)
    async def _handle_document_missing(
        request: Request, exc: DocumentNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
        )

    @app.exception_handler(DocumentTooLargeError)
    async def _handle_document_too_large(
        request: Request, exc: DocumentTooLargeError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(HealthcareAssistantError)
    async def _handle_domain_error(
        request: Request, exc: HealthcareAssistantError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)}
        )


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(alerts_router, prefix=settings.api_prefix)
    app.include_router(documents_router, prefix=settings.api_prefix)
    app.include_router(health_assessment_router, prefix=settings.api_prefix)
    app.include_router(risk_router, prefix=settings.api_prefix)
    app.include_router(vitals_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["Health"], summary="Service health check")
    def health_check() -> dict[str, str]:
        """Return a simple liveness payload."""
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    return app


app = create_app()