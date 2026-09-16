"""FastAPI routers for the healthcare assistant API."""

from backend.api.routes.auth import router as auth_router
from backend.api.routes.alerts import router as alerts_router
from backend.api.routes.documents import router as documents_router
from backend.api.routes.health_assessment import router as health_assessment_router
from backend.api.routes.risk import router as risk_router
from backend.api.routes.vitals import router as vitals_router

__all__ = [
	"alerts_router",
	"auth_router",
	"documents_router",
	"health_assessment_router",
	"risk_router",
	"vitals_router",
]