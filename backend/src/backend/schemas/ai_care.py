"""Request and response models for the AI Care chat assistant."""

from pydantic import BaseModel, Field


class AiCareChatRequest(BaseModel):
    """A patient question sent to AI Care."""

    message: str = Field(min_length=1, max_length=4000)


class AiCareSource(BaseModel):
    """A report excerpt used to ground an AI Care answer."""

    filename: str | None = None
    document_type: str | None = None
    excerpt: str


class AiCareChatResponse(BaseModel):
    """The generated answer and its grounding metadata."""

    answer: str
    context_used: bool
    sources: list[AiCareSource] = Field(default_factory=list)
    provider: str
    disclaimer: str