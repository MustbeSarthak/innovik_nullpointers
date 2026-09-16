"""Focused tests for patient memory retrieval and medical knowledge indexing."""

from pathlib import Path

import pytest

from backend.core.config import get_settings
from backend.memory.agent import MemoryAgent, build_memory_graph
from backend.rag.embeddings import reset_embedding_cache
from backend.rag.ingest import (
    index_document,
    index_medical_knowledge,
    index_medical_knowledge_directory,
    query_medical_knowledge,
    reset_vector_store,
)
from backend.rag.loaders import LoadedDocument


@pytest.fixture(autouse=True)
def isolated_rag() -> None:
    settings = get_settings()
    settings.embedding_provider = "hashing"
    settings.chroma_mode = "ephemeral"
    settings.rag_relevance_distance = 0.9
    reset_embedding_cache()
    reset_vector_store()
    yield
    reset_vector_store()
    reset_embedding_cache()


def _document(text: str, pages: int = 1) -> LoadedDocument:
    return LoadedDocument(text=text, pages=pages, suffix=".txt")


def test_memory_retrieves_relevant_history_from_multiple_documents() -> None:
    index_document(
        101,
        7,
        _document("Metformin 500 mg twice daily was prescribed for diabetes."),
        filename="prescription.txt",
        document_type="prescription",
    )
    index_document(
        102,
        7,
        _document("Blood report: HbA1c 7.2 percent. Doctor observation: stable."),
        filename="blood-report.txt",
        document_type="blood_report",
    )

    context = MemoryAgent().retrieve_context(7, "diabetes metformin HbA1c")

    assert context.available is True
    assert context.status == "available"
    assert context.patient_id == 7
    assert context.medications
    assert context.lab_reports
    assert {source.document_id for source in context.excerpts} == {"101", "102"}
    assert {source.filename for source in context.excerpts} == {
        "prescription.txt",
        "blood-report.txt",
    }
    assert all(source.page_count == 1 for source in context.excerpts)
    assert all(source.chunk_index == 0 for source in context.excerpts)


def test_memory_enforces_patient_isolation() -> None:
    index_document(
        201,
        1,
        _document("Patient has a severe penicillin allergy."),
        filename="allergy.txt",
        document_type="report",
    )
    index_document(
        202,
        2,
        _document("Patient takes insulin for diabetes."),
        filename="medications.txt",
        document_type="prescription",
    )

    context = MemoryAgent().retrieve_context(1, "insulin diabetes")

    assert context.available is False
    assert context.excerpts == []
    assert all("insulin" not in item for item in context.medications)


def test_memory_returns_explicit_unavailable_context_for_no_match() -> None:
    index_document(
        301,
        3,
        _document("The patient attended a routine follow-up appointment."),
        filename="visit.txt",
        document_type="report",
    )

    context = MemoryAgent().retrieve_context(3, "rare genomic marker ZXQ-991")

    assert context.available is False
    assert context.status == "unavailable"
    assert context.excerpts == []
    assert context.diagnoses == []
    assert context.historical_events == []


def test_memory_graph_executes_the_expected_workflow() -> None:
    index_document(
        401,
        4,
        _document("Discharge summary records recovery after treatment."),
        filename="discharge.txt",
        document_type="discharge_summary",
    )

    result = build_memory_graph().invoke({"patient_id": 4, "query": "treatment"})

    assert result["context"].available is True
    assert result["context"].historical_events


def test_medical_knowledge_uses_a_separate_collection() -> None:
    index_medical_knowledge(
        "reference-1",
        _document("General guidance: metformin is used for type 2 diabetes."),
        filename="diabetes-guide.txt",
        document_type="guideline",
    )

    records = query_medical_knowledge("metformin diabetes")

    assert records
    assert records[0]["metadata"]["scope"] == "medical_knowledge"
    assert records[0]["metadata"]["source_id"] == "reference-1"


def test_medical_knowledge_directory_indexes_supported_files(tmp_path: Path) -> None:
    (tmp_path / "hypertension.md").write_text(
        "General hypertension treatment guidance.", encoding="utf-8"
    )
    (tmp_path / "ignore.csv").write_text("not indexed", encoding="utf-8")

    results = index_medical_knowledge_directory(tmp_path)

    assert [result.source_id for result in results] == ["hypertension"]
    records = query_medical_knowledge("hypertension treatment")
    assert records[0]["metadata"]["filename"] == "hypertension.md"
