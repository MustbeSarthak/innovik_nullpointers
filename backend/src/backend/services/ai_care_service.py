"""Groq-backed AI Care chat with optional patient-report grounding."""

from langchain_groq import ChatGroq

from backend.core.config import get_settings
from backend.core.exceptions import MemoryAgentError
from backend.rag.ingest import query_patient_records
from backend.schemas.ai_care import AiCareChatResponse, AiCareSource


DISCLAIMER = (
    "AI Care provides general educational guidance and is not a medical diagnosis. "
    "For emergencies, contact local emergency services or a qualified clinician."
)


def _report_context(patient_id: int, message: str) -> tuple[str, list[AiCareSource]]:
    """Retrieve only relevant report excerpts owned by the current patient."""
    settings = get_settings()
    records = query_patient_records(
        patient_id,
        message,
        top_k=settings.ai_care_max_context_excerpts,
    )
    sources: list[AiCareSource] = []
    excerpts: list[str] = []
    for record in records:
        metadata = record.get("metadata") or {}
        excerpt = str(record.get("text") or "").strip()
        if not excerpt:
            continue
        sources.append(
            AiCareSource(
                filename=metadata.get("filename"),
                document_type=metadata.get("document_type"),
                excerpt=excerpt,
            )
        )
        excerpts.append(
            f"Source: {metadata.get('filename') or 'patient report'}\n{excerpt}"
        )
    return "\n\n".join(excerpts), sources


def chat_with_ai_care(patient_id: int, message: str) -> AiCareChatResponse:
    """Answer with Groq, grounding the answer in RAG context when available."""
    settings = get_settings()
    if not settings.groq_api_key:
        raise MemoryAgentError("GROQ_API_KEY is not configured")

    context = ""
    sources: list[AiCareSource] = []
    try:
        context, sources = _report_context(patient_id, message)
    except Exception:
        # A retrieval failure must not prevent general AI Care answers.
        context = ""
        sources = []

    context_section = (
        "Relevant excerpts from the patient's uploaded reports:\n"
        f"{context}"
        if context
        else "No relevant uploaded-report excerpts were found. Answer from general medical knowledge."
    )
    prompt = f"""You are AI Care, a careful health education assistant.

{context_section}

User question:
{message}

Instructions:
- Answer the user's question directly and clearly.
- Use report excerpts only as context; never invent patient facts.
- Explain uncertainty when the reports do not answer the question.
- Give practical, low-risk next steps when appropriate.
- Mention urgent medical care for emergency symptoms.
- Do not claim to diagnose, prescribe, or replace a clinician.
"""

    try:
        model = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.2,
            timeout=settings.groq_timeout_seconds,
            max_retries=1,
        )
        result = model.invoke(prompt)
        answer = str(result.content).strip()
    except Exception as exc:
        raise MemoryAgentError(f"AI Care could not generate a response: {exc}") from exc

    if not answer:
        raise MemoryAgentError("AI Care returned an empty response")
    return AiCareChatResponse(
        answer=answer,
        context_used=bool(sources),
        sources=sources,
        provider=f"groq:{settings.groq_model}",
        disclaimer=DISCLAIMER,
    )