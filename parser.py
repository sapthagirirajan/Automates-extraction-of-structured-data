"""Bytes -> plain text. No LLM here.

You are responsible for the three TODOs below. Keep this module deterministic:
identical input bytes -> identical output text. The cache layer in main.py
relies on that.
"""

from __future__ import annotations

from typing import Literal

Format = Literal["pdf", "docx", "unknown"]


def detect_format(file_bytes: bytes) -> Format:
    """Detect file format from magic bytes.

    Hints:
    - PDF starts with b"%PDF-"
    - DOCX is a zip; its first bytes are b"PK\\x03\\x04"
    - Everything else -> "unknown"

    Do NOT trust the upload's Content-Type header or filename extension.
    """
    if file_bytes.startswith(b"%PDF-"):
        return "pdf"
    if file_bytes.startswith(b"PK\x03\x04"):
        return "docx"
    return "unknown"


def parse_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber, fallback to pypdf.

    Requirements:
    - Preserve newlines BETWEEN pages (the LLM uses them as layout cues).
    - Strip leading/trailing whitespace per line, but keep blank lines.
    - Return "" (not None) for fully-scanned/empty PDFs.
    """
    import io

    # Try pdfplumber first (better text extraction)
    try:
        import pdfplumber
        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if not text:
                    pages.append("")
                    continue
                lines = [line.strip() for line in text.splitlines()]
                pages.append("\n".join(lines).strip())
        return "\n\n".join(pages).strip()
    except ImportError:
        pass  # Fall through to pypdf
    except Exception:
        pass  # Fall through to pypdf
    
    # Fallback to pypdf (minimal dependencies, no charset_normalizer issues)
    try:
        from pypdf import PdfReader
        pages: list[str] = []
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            text = page.extract_text() or ""
            if not text:
                pages.append("")
                continue
            lines = [line.strip() for line in text.splitlines()]
            pages.append("\n".join(lines).strip())
        return "\n\n".join(pages).strip()
    except Exception as e:
        # Scanned/corrupted PDF
        print(f"Warning: PDF parsing failed ({type(e).__name__}), treating as scanned PDF", flush=True)
        return ""


def parse_docx(file_bytes: bytes) -> str:
    """Extract plain text from DOCX bytes using python-docx.

    Requirements:
    - Concatenate paragraph text with newlines.
    - Skip purely-empty paragraphs.
    """
    import io

    from docx import Document

    paragraphs: list[str] = []
    doc = Document(io.BytesIO(file_bytes))
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs).strip()


def parse(file_bytes: bytes) -> tuple[Format, str]:
    """Top-level entry point used by main.py.

    Returns (format, text). Raises ValueError on "unknown" format.
    """
    fmt = detect_format(file_bytes)
    if fmt == "pdf":
        return fmt, parse_pdf(file_bytes)
    if fmt == "docx":
        return fmt, parse_docx(file_bytes)
    raise ValueError(f"unsupported file format: {fmt}")
