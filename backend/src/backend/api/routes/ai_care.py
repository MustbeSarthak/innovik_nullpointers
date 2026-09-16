"""AI Care chat endpoint."""

from fastapi import APIRouter

from backend.api.deps import CurrentPatient
from backend.schemas.ai_care import AiCareChatRequest, AiCareChatResponse
from backend.services.ai_care_service import chat_with_ai_care

router = APIRouter(prefix="/ai-care", tags=["AI Care"])


@router.post("/chat", response_model=AiCareChatResponse)
def chat(request: AiCareChatRequest, patient: CurrentPatient) -> AiCareChatResponse:
    """Answer a patient question using Groq and optional report context."""
    return chat_with_ai_care(patient.id, request.message.strip())