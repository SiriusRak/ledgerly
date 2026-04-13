"""PDF text extraction with pdfplumber, Gemini Vision fallback."""

from io import BytesIO
from typing import Literal

import pdfplumber

from app.config import settings

MAX_CHARS = 30_000
MIN_PLUMBER_CHARS = 50


def extract_text(pdf_bytes: bytes) -> tuple[str, Literal["pdfplumber", "gemini"]]:
    """Extract text from PDF bytes. Returns (text, source)."""
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    if len(text.strip()) >= MIN_PLUMBER_CHARS:
        return text[:MAX_CHARS], "pdfplumber"

    # Fallback: Gemini Vision for scanned/image PDFs
    return _gemini_vision_extract(pdf_bytes), "gemini"


def _gemini_vision_extract(pdf_bytes: bytes) -> str:
    """Use Gemini Vision to OCR a PDF. Requires GEMINI_API_KEY."""
    if not settings.gemini_api_key:
        raise RuntimeError(
            "PDF has no extractable text and GEMINI_API_KEY not configured"
        )

    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(
        [
            "Extract all text from this invoice PDF. Return raw text only, no formatting.",
            {"mime_type": "application/pdf", "data": pdf_bytes},
        ]
    )
    text = response.text or ""
    return text[:MAX_CHARS]
