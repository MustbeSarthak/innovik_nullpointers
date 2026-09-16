"""LangGraph workflow for grounded patient medical-context retrieval."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from backend.core.exceptions import MemoryAgentError
from backend.rag.ingest import query_patient_records
from backend.memory.schemas import (
    MedicalContext,
    MedicalContextSource,
    MemoryAgentRequest,
    MemoryAgentState,
)


def _retrieve_node(state: MemoryAgentState) -> dict[str, Any]:
    """Retrieve only records belonging to the requested patient."""
    return {
        "records": query_patient_records(
            state["patient_id"],
            state["query"],
        )
    }


def _organize_node(state: MemoryAgentState) -> dict[str, Any]:
    """Normalize retrieval results without inventing facts."""
    organized: list[MedicalContextSource] = []
    for record in state.get("records", []):
        metadata = record.get("metadata") or {}
        organized.append(
            MedicalContextSource(
                text=str(record.get("text", "")),
                distance=record.get("distance"),
                document_id=_optional_string(metadata.get("document_id")),
                filename=_optional_string(metadata.get("filename")),
                document_type=_optional_string(metadata.get("document_type")),
                page_count=_optional_int(metadata.get("page_count")),
                chunk_index=_optional_int(metadata.get("chunk_index")),
                created_at=_optional_string(metadata.get("created_at")),
                **{
                    key: value
                    for key, value in metadata.items()
                    if key
                    not in {
                        "document_id",
                        "filename",
                        "document_type",
                        "page_count",
                        "chunk_index",
                        "created_at",
                    }
                },
            )
        )
    return {"organized_records": organized}


def _build_context_node(state: MemoryAgentState) -> dict[str, Any]:
    """Build a structured, explicitly unavailable context when no records match."""
    excerpts = state.get("organized_records", [])
    categories: dict[str, list[str]] = {
        "diagnoses": [],
        "symptoms": [],
        "medications": [],
        "allergies": [],
        "lab_reports": [],
        "treatments": [],
        "observations": [],
        "historical_events": [],
    }
    for excerpt in excerpts:
        target = _category_for_document(excerpt.document_type)
        if target is not None and excerpt.text:
            categories[target].append(excerpt.text)
    context = MedicalContext(
        patient_id=state["patient_id"],
        query=state["query"],
        available=bool(excerpts),
        status="available" if excerpts else "unavailable",
        excerpts=excerpts,
        **categories,
    )
    return {"context": context}


def _return_context_node(state: MemoryAgentState) -> dict[str, Any]:
    """Validate that the graph always produces its final context object."""
    if "context" not in state:
        raise MemoryAgentError("memory graph completed without a medical context")
    return state


def _category_for_document(document_type: str | None) -> str | None:
    """Map source labels to broad buckets without interpreting document text."""
    return {
        "prescription": "medications",
        "discharge_summary": "historical_events",
        "blood_report": "lab_reports",
        "ecg_report": "lab_reports",
        "report": "observations",
    }.get(document_type)


def _optional_string(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def build_memory_graph() -> Any:
    """Compile the reusable patient-context LangGraph workflow."""
    graph = StateGraph(MemoryAgentState)
    graph.add_node("receive_request", lambda state: state)
    graph.add_node("retrieve_patient_records", _retrieve_node)
    graph.add_node("organize_records", _organize_node)
    graph.add_node("build_context", _build_context_node)
    graph.add_node("return_context", _return_context_node)
    graph.add_edge(START, "receive_request")
    graph.add_edge("receive_request", "retrieve_patient_records")
    graph.add_edge("retrieve_patient_records", "organize_records")
    graph.add_edge("organize_records", "build_context")
    graph.add_edge("build_context", "return_context")
    graph.add_edge("return_context", END)
    return graph.compile()


class MemoryAgent:
    """Modular facade for downstream agents requesting patient context."""

    def __init__(self, graph: Any | None = None) -> None:
        self.graph = graph or build_memory_graph()

    def retrieve_context(self, patient_id: int, query: str) -> MedicalContext:
        """Run the workflow and return grounded context for one patient."""
        request = MemoryAgentRequest(patient_id=patient_id, query=query.strip())
        result = self.graph.invoke(request.model_dump())
        context = result.get("context")
        if not isinstance(context, MedicalContext):
            raise MemoryAgentError("memory graph returned an invalid medical context")
        return context

    def invoke(self, request: MemoryAgentRequest) -> MedicalContext:
        """Invoke the agent using a typed request model."""
        return self.retrieve_context(request.patient_id, request.query)
