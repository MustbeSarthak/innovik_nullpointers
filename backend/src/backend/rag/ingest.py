"""Chroma-backed ingestion and retrieval for patient documents.

The module is deliberately framework-free.  File decoding stays in
:mod:`backend.rag.loaders`, while this module owns chunking, vector-store
lifecycle, and patient-scoped records.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.core.config import get_settings
from backend.core.exceptions import DocumentIngestionError, VectorStoreError
from backend.rag.embeddings import get_embeddings
from backend.rag.loaders import LoadedDocument, load_document


@dataclass(frozen=True)
class IngestionResult:
    """Summary returned after a document has been indexed."""

    document_id: int | str
    patient_id: int
    page_count: int
    chunk_count: int
    chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeIngestionResult:
    """Summary returned after indexing one general medical-knowledge source."""

    source_id: str
    page_count: int
    chunk_count: int
    chunk_ids: tuple[str, ...]


_client: Any | None = None
_collections: dict[str, Any] = {}


def _load_chromadb() -> Any:
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise VectorStoreError(
            "The 'chromadb' package is required for document indexing. "
            "Install it with: uv add chromadb"
        ) from exc
    return chromadb


def get_chroma_client() -> Any:
    """Return the lazily-created persistent or ephemeral Chroma client."""
    global _client
    if _client is not None:
        return _client
    chromadb = _load_chromadb()
    settings = get_settings()
    try:
        if settings.chroma_mode.strip().lower() == "ephemeral":
            _client = chromadb.EphemeralClient()
        elif settings.chroma_mode.strip().lower() == "persistent":
            _client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
        else:
            raise VectorStoreError(
                "unsupported CHROMA_MODE; expected 'persistent' or 'ephemeral'"
            )
    except VectorStoreError:
        raise
    except Exception as exc:
        raise VectorStoreError(f"could not initialise Chroma: {exc}") from exc
    return _client


def get_collection(name: str | None = None) -> Any:
    """Return a configured Chroma collection without eagerly loading a model."""
    settings = get_settings()
    collection_name = name or settings.collection_patient_records
    collection = _collections.get(collection_name)
    if collection is not None:
        return collection
    try:
        collection = get_chroma_client().get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as exc:
        raise VectorStoreError(
            f"could not open Chroma collection {collection_name!r}: {exc}"
        ) from exc
    _collections[collection_name] = collection
    return collection


def split_text(
    text: str, chunk_size: int | None = None, chunk_overlap: int | None = None
) -> list[str]:
    """Split text into bounded, overlapping chunks while preserving content."""
    settings = get_settings()
    size = chunk_size or settings.rag_chunk_size
    overlap = settings.rag_chunk_overlap if chunk_overlap is None else chunk_overlap
    if size <= 0 or overlap < 0 or overlap >= size:
        raise DocumentIngestionError(
            "chunk_size must be positive and chunk_overlap must be less than it"
        )
    clean = text.strip()
    if not clean:
        raise DocumentIngestionError("cannot index an empty document")
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + size, len(clean))
        if end < len(clean):
            boundary = max(clean.rfind("\n", start, end), clean.rfind(" ", start, end))
            if boundary > start:
                end = boundary
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        next_start = end - overlap
        start = next_start if next_start > start else end
    return chunks


def _record_id(document_id: int | str, chunk_index: int) -> str:
    return f"document-{document_id}-chunk-{chunk_index}"


def _knowledge_record_id(source_id: str, chunk_index: int) -> str:
    return f"knowledge-{source_id}-chunk-{chunk_index}"


def _index_chunks(
    *,
    record_ids: tuple[str, ...],
    chunks: list[str],
    metadata: list[dict[str, Any]],
    collection_name: str,
    record_label: str,
) -> None:
    """Embed and upsert chunks into exactly one explicitly selected collection."""
    try:
        embeddings = get_embeddings()(chunks)
        get_collection(collection_name).upsert(
            ids=list(record_ids),
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadata,
        )
    except DocumentIngestionError:
        raise
    except Exception as exc:
        raise VectorStoreError(f"could not index {record_label}: {exc}") from exc


def index_document(
    document_id: int | str,
    patient_id: int,
    document: LoadedDocument,
    *,
    filename: str = "",
    document_type: str = "other",
    created_at: str | None = None,
    collection_name: str | None = None,
) -> IngestionResult:
    """Embed and upsert one patient document into Chroma."""
    chunks = split_text(document.text)
    ids = tuple(_record_id(document_id, index) for index in range(len(chunks)))
    settings = get_settings()
    metadata = []
    for index in range(len(chunks)):
        item = {
            "scope": "patient_record",
            "patient_id": patient_id,
            "document_id": str(document_id),
            "filename": filename,
            "document_type": document_type,
            "page_count": document.pages,
            "chunk_index": index,
        }
        if created_at is not None:
            item["created_at"] = created_at
        metadata.append(item)
    _index_chunks(
        record_ids=ids,
        chunks=chunks,
        metadata=metadata,
        collection_name=collection_name or settings.collection_patient_records,
        record_label=f"document {document_id}",
    )
    return IngestionResult(
        document_id=document_id,
        patient_id=patient_id,
        page_count=document.pages,
        chunk_count=len(chunks),
        chunk_ids=ids,
    )


def ingest_document(*args: Any, **kwargs: Any) -> IngestionResult:
    """Compatibility alias for :func:`index_document`."""
    return index_document(*args, **kwargs)


def index_medical_knowledge(
    source_id: str,
    document: LoadedDocument,
    *,
    filename: str = "",
    document_type: str = "reference",
    source: str | None = None,
    collection_name: str | None = None,
) -> KnowledgeIngestionResult:
    """Index general medical knowledge separately from patient records."""
    settings = get_settings()
    chunks = split_text(document.text)
    ids = tuple(_knowledge_record_id(source_id, index) for index in range(len(chunks)))
    metadata = [
        {
            "scope": "medical_knowledge",
            "source_id": source_id,
            "filename": filename,
            "document_type": document_type,
            "source": source or filename,
            "page_count": document.pages,
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]
    _index_chunks(
        record_ids=ids,
        chunks=chunks,
        metadata=metadata,
        collection_name=collection_name or settings.collection_medical_knowledge,
        record_label=f"medical knowledge source {source_id}",
    )
    return KnowledgeIngestionResult(
        source_id=source_id,
        page_count=document.pages,
        chunk_count=len(chunks),
        chunk_ids=ids,
    )


def index_medical_knowledge_directory(
    directory: str | Path | None = None,
) -> list[KnowledgeIngestionResult]:
    """Index every supported file in the configured medical-knowledge directory."""
    settings = get_settings()
    root = Path(directory or settings.medical_knowledge_directory)
    if not root.is_dir():
        raise DocumentIngestionError(f"medical knowledge directory {root} does not exist")
    results: list[KnowledgeIngestionResult] = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower() in (".pdf", ".txt", ".md", ".markdown", ".text"):
            results.append(
                index_medical_knowledge(
                    source_id=path.stem,
                    document=load_document(path),
                    filename=path.name,
                    source=str(path),
                )
            )
    return results


def query_patient_records(
    patient_id: int,
    query: str,
    *,
    top_k: int | None = None,
    document_id: int | str | None = None,
    collection_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return the nearest patient-owned document chunks for ``query``."""
    settings = get_settings()
    query_text = query.strip()
    if not query_text:
        raise DocumentIngestionError("query must not be empty")
    if len(query_text) > settings.rag_max_query_length:
        raise DocumentIngestionError(
            f"query exceeds the maximum length of {settings.rag_max_query_length}"
        )
    limit = top_k or settings.rag_top_k
    if limit <= 0:
        raise DocumentIngestionError("top_k must be greater than zero")
    where: dict[str, Any] = {"patient_id": patient_id}
    if document_id is not None:
        where = {"$and": [where, {"document_id": str(document_id)}]}
    try:
        result = get_collection(collection_name).query(
            query_embeddings=get_embeddings()([query_text]),
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        raise VectorStoreError(f"could not query patient records: {exc}") from exc
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return [
        {
            "text": str(text)[: settings.rag_max_excerpt_length],
            "metadata": metadata or {},
            "distance": distance,
        }
        for text, metadata, distance in zip(documents, metadatas, distances)
        if distance is None or distance <= settings.rag_relevance_distance
    ]


def query_medical_knowledge(
    query: str,
    *,
    top_k: int | None = None,
    collection_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return general medical knowledge, never mixed into patient history."""
    settings = get_settings()
    query_text = query.strip()
    if not query_text:
        raise DocumentIngestionError("query must not be empty")
    if len(query_text) > settings.rag_max_query_length:
        raise DocumentIngestionError(
            f"query exceeds the maximum length of {settings.rag_max_query_length}"
        )
    limit = top_k or settings.rag_top_k
    if limit <= 0:
        raise DocumentIngestionError("top_k must be greater than zero")
    try:
        result = get_collection(
            collection_name or settings.collection_medical_knowledge
        ).query(
            query_embeddings=get_embeddings()([query_text]),
            n_results=limit,
            where={"scope": "medical_knowledge"},
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        raise VectorStoreError(f"could not query medical knowledge: {exc}") from exc
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return [
        {
            "text": str(text)[: settings.rag_max_excerpt_length],
            "metadata": metadata or {},
            "distance": distance,
        }
        for text, metadata, distance in zip(documents, metadatas, distances)
        if distance is None or distance <= settings.rag_relevance_distance
    ]


def delete_document(
    document_id: int | str,
    patient_id: int,
    *,
    collection_name: str | None = None,
) -> None:
    """Delete all vector chunks for one patient-owned document."""
    try:
        get_collection(collection_name).delete(
            where={
                "$and": [
                    {"patient_id": patient_id},
                    {"document_id": str(document_id)},
                ]
            }
        )
    except Exception as exc:
        raise VectorStoreError(f"could not delete document {document_id}: {exc}") from exc


def reset_vector_store() -> None:
    """Forget lazy clients and collections; useful for isolated test runs."""
    global _client
    _collections.clear()
    _client = None
