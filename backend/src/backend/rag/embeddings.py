"""Embedding providers for the RAG pipeline — Module 4.

Two providers are available:

``sentence-transformers``
    The production provider.  The model is loaded lazily (first embedding call)
    so importing this module never downloads anything, and a load failure
    surfaces as a clear
    :class:`~backend.core.exceptions.EmbeddingUnavailableError`.

``hashing``
    A deterministic, dependency-free fallback used by the test-suite and by
    air-gapped environments where the model cannot be downloaded.  It hashes
    word tokens into a fixed-size L2-normalised vector, so lexical overlap still
    produces a usable similarity ordering - it is explicitly *not* a semantic
    model and must not be used for real clinical ranking.

Both providers are plain callables (``list[str] -> list[list[float]]``), which
is exactly what Chroma's ``embedding_function`` parameter accepts.
"""

import hashlib
import math
import os
import re
import threading
from typing import Any, Protocol, runtime_checkable

from backend.core.config import get_settings
from backend.core.exceptions import EmbeddingUnavailableError

HASHING_PROVIDER = "hashing"
SENTENCE_TRANSFORMERS_PROVIDER = "sentence-transformers"
SUPPORTED_PROVIDERS = (SENTENCE_TRANSFORMERS_PROVIDER, HASHING_PROVIDER)

# Simple word tokeniser - sufficient for the deterministic hashing provider.
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@runtime_checkable
class EmbeddingFunction(Protocol):
    """Structural type of an embedding callable."""

    def __call__(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        """Return one embedding vector per input text."""
        ...


def _tokenize(text: str) -> list[str]:
    """Return the lower-case word tokens of ``text``."""
    return _TOKEN_PATTERN.findall(text.lower())


class HashingEmbeddings:
    """Deterministic hashed bag-of-words embeddings (offline fallback).

    Args:
        dimensions: Size of the produced vectors.  The default matches the
            ``all-MiniLM-L6-v2`` output size so both providers can be swapped
            inside the same collection.
    """

    def __init__(self, dimensions: int = 384) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        self.dimensions = dimensions
        self.name = HASHING_PROVIDER

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """Embed ``texts`` deterministically."""
        if isinstance(texts, str):  # pragma: no cover - defensive convenience
            texts = [texts]
        return [self.embed_document(text) for text in texts]

    def embed_document(self, text: str) -> list[float]:
        """Embed a single ``text`` into an L2-normalised vector."""
        vector = [0.0] * self.dimensions
        for token in _tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            # Empty / stop-word-only text: return a fixed unit vector so Chroma
            # and the cosine distance stay well defined.
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]


class SentenceTransformerEmbeddings:
    """``sentence-transformers`` embeddings loaded lazily on first use.

    Args:
        model_name: Hugging Face model id, e.g.
            ``sentence-transformers/all-MiniLM-L6-v2``.
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.name = SENTENCE_TRANSFORMERS_PROVIDER
        self._model: Any | None = None
        self._lock = threading.Lock()

    def _load_model(self) -> Any:
        """Import and instantiate the model exactly once (thread-safe).

        Raises:
            EmbeddingUnavailableError: when ``sentence-transformers`` is not
                installed or the model cannot be loaded.
        """
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:  # pragma: no cover - double-checked lock
                return self._model
            try:
                from sentence_transformers import (  # type: ignore[import-not-found]
                    SentenceTransformer,
                )
            except ImportError as exc:
                raise EmbeddingUnavailableError(
                    "The 'sentence-transformers' package is required for the "
                    "'sentence-transformers' embedding provider. Install it with: "
                    "uv add sentence-transformers"
                ) from exc
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:  # download failure / incompatible torch, ...
                raise EmbeddingUnavailableError(
                    f"could not load embedding model {self.model_name!r}: {exc}"
                ) from exc
        return self._model

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """Embed ``texts`` with the configured sentence-transformer model."""
        if isinstance(texts, str):  # pragma: no cover - defensive convenience
            texts = [texts]
        model = self._load_model()
        vectors = model.encode(
            list(texts), normalize_embeddings=True, convert_to_numpy=True
        )
        return [[float(value) for value in vector] for vector in vectors]


def resolve_provider_name(provider: str | None = None) -> str:
    """Return the embedding provider to use.

    Environment variables win over the cached settings object so the test-suite
    can switch providers after the application has been imported.
    """
    name = (
        provider
        or os.environ.get("EMBEDDING_PROVIDER")
        or get_settings().embedding_provider
    )
    return name.strip().lower()


def resolve_model_name(model_name: str | None = None) -> str:
    """Return the sentence-transformers model id to use."""
    return (
        model_name or os.environ.get("EMBEDDING_MODEL") or get_settings().embedding_model
    ).strip()


def resolve_dimensions(dimensions: int | None = None) -> int:
    """Return the vector size used by the hashing provider."""
    if dimensions is not None:
        return dimensions
    raw = os.environ.get("EMBEDDING_DIMENSIONS")
    if raw and raw.isdigit():
        return int(raw)
    return get_settings().embedding_dimensions


_cache: dict[tuple[str, str, int], EmbeddingFunction] = {}
_cache_lock = threading.Lock()


def get_embeddings(
    provider: str | None = None, model_name: str | None = None
) -> EmbeddingFunction:
    """Return the (cached) embedding callable for the configured provider.

    Args:
        provider: Optional provider override (``sentence-transformers`` or
            ``hashing``).
        model_name: Optional model override for the sentence-transformers
            provider.

    Returns:
        A callable that turns a list of texts into a list of float vectors.

    Raises:
        EmbeddingUnavailableError: when ``provider`` is not supported.
    """
    name = resolve_provider_name(provider)
    model = resolve_model_name(model_name)
    dimensions = resolve_dimensions()
    key = (name, model, dimensions)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached
        if name == HASHING_PROVIDER:
            embeddings: EmbeddingFunction = HashingEmbeddings(dimensions)
        elif name == SENTENCE_TRANSFORMERS_PROVIDER:
            embeddings = SentenceTransformerEmbeddings(model)
        else:
            raise EmbeddingUnavailableError(
                f"unsupported embedding provider {name!r}; expected one of "
                f"{', '.join(SUPPORTED_PROVIDERS)}"
            )
        _cache[key] = embeddings
        return embeddings


def reset_embedding_cache() -> None:
    """Drop the cached providers (used by the test-suite)."""
    with _cache_lock:
        _cache.clear()
