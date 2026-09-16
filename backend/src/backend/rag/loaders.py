"""Document loaders for the RAG pipeline — Module 4.

The first stage of the pipeline is ``Document -> Loader``:

    Patient upload (PDF)            -> :func:`load_pdf`
    Plain-text / markdown reference -> :func:`load_text`
    Anything else                   -> :func:`load_document` (dispatch by suffix)

``pypdf`` is imported lazily, mirroring the way Module 1 treats the optional
``fastmcp`` dependency: importing this module never fails, but calling a PDF
loader without ``pypdf`` installed raises a clear
:class:`~backend.core.exceptions.DocumentIngestionError`.
"""

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from backend.core.exceptions import (
    DocumentIngestionError,
    UnsupportedDocumentTypeError,
)

# Suffixes the loader understands.  ``.pdf`` is the format patients upload.
PDF_SUFFIXES = (".pdf",)
TEXT_SUFFIXES = (".txt", ".md", ".markdown", ".text")
SUPPORTED_SUFFIXES = PDF_SUFFIXES + TEXT_SUFFIXES

# Content types accepted by the upload endpoint.
PDF_CONTENT_TYPES = ("application/pdf",)
TEXT_CONTENT_TYPES = ("text/plain", "text/markdown", "text/x-markdown")
SUPPORTED_CONTENT_TYPES = PDF_CONTENT_TYPES + TEXT_CONTENT_TYPES


@dataclass(frozen=True)
class LoadedDocument:
    """Text plus metadata produced by a loader.

    Attributes:
        text: The extracted document text (pages joined by blank lines).
        pages: Number of pages (``1`` for plain-text files).
        suffix: Normalised file suffix, e.g. ``.pdf``.
        metadata: Extra loader metadata (``page_count``, ``loader``, ...).
    """

    text: str
    pages: int
    suffix: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when the loader extracted no usable text."""
        return not self.text.strip()


def _load_pdf_reader() -> Any:
    """Import :class:`pypdf.PdfReader` lazily.

    Raises:
        DocumentIngestionError: when ``pypdf`` is not installed.
    """
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise DocumentIngestionError(
            "The 'pypdf' package is required to read PDF documents. "
            "Install it with: uv add pypdf"
        ) from exc
    return PdfReader


def load_pdf(source: str | Path | BinaryIO | bytes) -> LoadedDocument:
    """Extract the text of a PDF document with PyPDF.

    Args:
        source: A file path, an open binary stream or raw PDF bytes.

    Returns:
        A :class:`LoadedDocument` whose ``text`` concatenates every page.

    Raises:
        DocumentIngestionError: when the PDF cannot be parsed, is encrypted or
            contains no extractable text.
    """
    PdfReader = _load_pdf_reader()
    stream: Any = source
    opened_by_loader = False
    if isinstance(source, bytes):
        stream = io.BytesIO(source)
    elif isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise DocumentIngestionError(f"document {path} does not exist")
        stream = path.open("rb")
        opened_by_loader = True

    try:
        reader = PdfReader(stream)
        if getattr(reader, "is_encrypted", False):
            raise DocumentIngestionError(
                "encrypted PDF documents are not supported; upload an "
                "unprotected copy"
            )
        pages = [page.extract_text() or "" for page in reader.pages]
    except DocumentIngestionError:
        raise
    except Exception as exc:
        raise DocumentIngestionError(f"could not read PDF document: {exc}") from exc
    finally:
        # Only close streams this loader opened itself.
        if opened_by_loader:
            stream.close()

    text = "\n\n".join(page.strip() for page in pages).strip()
    if not text:
        raise DocumentIngestionError(
            "no extractable text found in the PDF document; scanned images "
            "need OCR before they can be indexed"
        )
    return LoadedDocument(
        text=text,
        pages=len(pages),
        suffix=".pdf",
        metadata={"page_count": len(pages), "loader": "pypdf"},
    )


def load_text(
    source: str | Path | BinaryIO | bytes, suffix: str = ".txt"
) -> LoadedDocument:
    """Read a plain-text document.

    Args:
        source: A file path, an open stream or raw bytes.
        suffix: Suffix recorded in the returned metadata.

    Returns:
        A :class:`LoadedDocument` with ``pages == 1``.

    Raises:
        DocumentIngestionError: when the file is missing or cannot be read.
    """
    try:
        if isinstance(source, bytes):
            raw = source
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise DocumentIngestionError(f"document {path} does not exist")
            raw = path.read_bytes()
        else:
            raw = source.read()
    except DocumentIngestionError:
        raise
    except Exception as exc:  # pragma: no cover - filesystem failure
        raise DocumentIngestionError(f"could not read text document: {exc}") from exc

    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        raise DocumentIngestionError("the text document is empty")
    return LoadedDocument(
        text=text,
        pages=1,
        suffix=suffix,
        metadata={"page_count": 1, "loader": "text"},
    )


def normalize_suffix(filename: str) -> str:
    """Return the lower-case suffix of ``filename`` (``""`` when absent)."""
    return Path(filename).suffix.lower()


def is_supported_suffix(filename: str) -> bool:
    """Return ``True`` when a loader knows how to read ``filename``."""
    return normalize_suffix(filename) in SUPPORTED_SUFFIXES


def load_document(source: str | Path) -> LoadedDocument:
    """Load ``source`` by dispatching on its file suffix.

    Args:
        source: Path of the document to load.

    Returns:
        The extracted :class:`LoadedDocument`.

    Raises:
        UnsupportedDocumentTypeError: when the suffix is not supported.
        DocumentIngestionError: when the content cannot be parsed.
    """
    path = Path(source)
    suffix = normalize_suffix(path.name)
    if suffix in PDF_SUFFIXES:
        return load_pdf(path)
    if suffix in TEXT_SUFFIXES:
        return load_text(path, suffix=suffix)
    raise UnsupportedDocumentTypeError(
        f"unsupported document type {suffix or '(none)'}; supported types are "
        f"{', '.join(SUPPORTED_SUFFIXES)}"
    )


def load_bytes(data: bytes, filename: str) -> LoadedDocument:
    """Load an uploaded file from its raw bytes.

    Args:
        data: Raw file content.
        filename: Original file name (used only to pick the loader).

    Returns:
        The extracted :class:`LoadedDocument`.

    Raises:
        UnsupportedDocumentTypeError: when the suffix is not supported.
        DocumentIngestionError: when the content cannot be parsed.
    """
    suffix = normalize_suffix(filename)
    if suffix in PDF_SUFFIXES:
        return load_pdf(data)
    if suffix in TEXT_SUFFIXES:
        return load_text(data, suffix=suffix)
    raise UnsupportedDocumentTypeError(
        f"unsupported document type {suffix or '(none)'}; supported types are "
        f"{', '.join(SUPPORTED_SUFFIXES)}"
    )