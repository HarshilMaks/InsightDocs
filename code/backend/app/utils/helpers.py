"""
Utility helpers used:
- UUID and timestamp helpers
- SHA256 content hashing
- Safe filename and S3 key helpers
- Text chunking for embeddings (word-based, with overlap)
- Lightweight file text extraction wrappers (PDF, docx, txt)
- Simple async retry decorator with exponential backoff
- Timing decorator for measuring function duration

"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Iterable, List, Optional

logger = logging.getLogger("insightops.helpers")
logger.setLevel(logging.INFO)


# ---------- Basic helpers ----------

def generate_uuid() -> str:
    """Return a UUID4 hex string."""
    return uuid.uuid4().hex


def utc_now() -> datetime:
    """Return current UTC datetime (tz-aware)."""
    return datetime.now(timezone.utc)


def ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


# ---------- Hashing / filenames ----------

def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hex digest for given bytes."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]")


def safe_filename(filename: str, max_length: int = 240) -> str:
    """
    Create a filesystem- and S3-friendly filename.
    Removes suspicious characters and truncates to max_length.
    """
    name = os.path.basename(filename)
    name = _SAFE_FILENAME_RE.sub("_", name)
    if len(name) > max_length:
        name = name[:max_length]
    return name


def build_s3_key(prefix: Optional[str], filename: str) -> str:
    """
    Build an S3 key from optional prefix and filename.
    Ensures no leading/trailing slashes and normalizes separators.
    """
    filename = safe_filename(filename)
    prefix = (prefix or "").strip().strip("/")
    if prefix:
        return f"{prefix}/{filename}"
    return filename


# ---------- Text chunking for embeddings ----------

def _word_tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer (keeps punctuation attached)."""
    return text.split()


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[str]:
    """
    Chunk `text` into overlapping segments suitable for embedding.
    Parameters:
      - chunk_size: approx number of words per chunk
      - overlap: number of words to overlap between chunks
    Uses a word-based approach (cheap but effective for most pipelines).
    """
    if not text:
        return []

    words = _word_tokenize(text)
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        overlap = 0

    chunks = []
    i = 0
    n = len(words)
    while i < n:
        j = min(i + chunk_size, n)
        chunk = " ".join(words[i:j])
        chunks.append(chunk)
        if j == n:
            break
        i = j - overlap  # step forward with overlap
        if i < 0:
            i = 0
    return chunks


# ---------- Lightweight file text extraction wrappers ----------

def _import_pypdf2():
    try:
        import PyPDF2  # type: ignore
        return PyPDF2
    except Exception:
        return None


def _import_docx():
    try:
        import docx  # type: ignore
        return docx
    except Exception:
        return None


def read_text_from_file(path: str, max_pages: Optional[int] = None) -> str:
    """
    Try to extract text from a file path.
    Supports: .txt, .md, .pdf (PyPDF2), .docx (python-docx)
    Raises RuntimeError with actionable message if required libs are missing.
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".csv"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    if ext == ".pdf":
        PyPDF2 = _import_pypdf2()
        if PyPDF2 is None:
            raise RuntimeError(
                "PyPDF2 is required to read PDF files. Install with: pip install PyPDF2"
            )
        text_parts = []
        with open(path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            pages_to_read = range(len(reader.pages)) if max_pages is None else range(min(max_pages, len(reader.pages)))
            for p in pages_to_read:
                try:
                    page = reader.pages[p]
                    text_parts.append(page.extract_text() or "")
                except Exception as exc:
                    logger.debug("PDF page read error: %s", exc)
        return "\n".join(text_parts)

    if ext in (".docx", ".doc"):
        docx = _import_docx()
        if docx is None:
            raise RuntimeError(
                "python-docx is required to read docx files. Install with: pip install python-docx"
            )
        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs if (p.text and p.text.strip())]
        return "\n".join(paragraphs)

    # Fallback: try binary -> decode
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        raise RuntimeError(f"Unsupported file type: {ext}")


# ---------- Async retry decorator ----------

def async_retry(
    tries: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Simple async retry decorator with exponential backoff.
    Usage:
        @async_retry(tries=4, delay=1, backoff=2)
        async def do_something(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            last_exc = None
            for attempt in range(1, _tries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    logger.debug("Attempt %d/%d failed: %s", attempt, _tries, exc)
                    if attempt == _tries:
                        break
                    await asyncio.sleep(_delay)
                    _delay *= backoff
            # re-raise the last exception
            raise last_exc
        return wrapper
    return decorator


# ---------- Timing decorator ----------

def timed(func: Callable):
    """
    Decorator to measure the execution time of sync functions.
    For async functions, use `async_timed`.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            t1 = time.perf_counter()
            logger.debug("Timed %s: %.3fs", func.__name__, t1 - t0)
    return wrapper


def async_timed(func: Callable):
    """Decorator to measure execution time of async functions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            t1 = time.perf_counter()
            logger.debug("Async timed %s: %.3fs", func.__name__, t1 - t0)
    return wrapper


# ---------- Small helpers ----------

def truncate_text(text: str, max_chars: int = 1000) -> str:
    """Truncate text cleanly for previews/logging."""
    if not text:
        return text
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."

def human_bytes(num: int) -> str:
    """Convert bytes to a human-friendly string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"{num:.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}PB"


# ---------- Example usage functions (for reference) ----------

def example_chunk_file_text(path: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Convenience helper: read a file, extract text and return chunks.
    Raises informative errors when extraction libs are missing.
    """
    text = read_text_from_file(path)
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)
