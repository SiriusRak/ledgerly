"""LLM field extraction via Groq JSON mode, Gemini fallback."""

import json
import signal
from typing import Optional

from pydantic import BaseModel, field_validator
from groq import Groq, RateLimitError

from app.config import settings

SYSTEM_PROMPT = """Tu extrais les champs comptables d'une facture fournisseur francaise.
Regles strictes :
- Ignore les totaux partiels, acomptes, reports, sous-totaux. Retourne UNIQUEMENT le total final.
- Si plusieurs taux TVA, somme les TVA et retourne le taux majoritaire.
- Dates au format ISO YYYY-MM-DD.
- Montants en nombres avec point decimal (pas de virgule). Exemple : 1234.56
- Champ absent -> null.
Retourne strictement le JSON conforme au schema suivant :
{
  "supplier_name": "string",
  "siret": "string or null",
  "invoice_date": "YYYY-MM-DD",
  "invoice_number": "string",
  "amount_ht": float,
  "amount_tva": float,
  "amount_ttc": float,
  "tva_rate": float
}"""

MODEL = "llama-3.3-70b-versatile"
TIMEOUT_SECONDS = 15


class InvoiceFields(BaseModel):
    supplier_name: str
    siret: Optional[str] = None
    invoice_date: str
    invoice_number: str
    amount_ht: float
    amount_tva: float
    amount_ttc: float
    tva_rate: float

    @field_validator("amount_ht", "amount_tva", "amount_ttc", "tva_rate", mode="before")
    @classmethod
    def coerce_to_float(cls, v):
        if v is None:
            return 0.0
        if isinstance(v, str):
            return float(v.replace(",", ".").replace(" ", ""))
        return float(v)

    @field_validator("siret", mode="before")
    @classmethod
    def coerce_siret(cls, v):
        if v is None:
            return None
        return str(v).strip() or None


class _TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise _TimeoutError("Groq request exceeded 15s timeout")


def extract_fields(text: str) -> dict:
    """Extract invoice fields from text using Groq LLM. Returns validated dict."""
    try:
        return _call_groq(text)
    except (RateLimitError, _TimeoutError):
        return _call_gemini_fallback(text)


def _call_groq(text: str) -> dict:
    """Call Groq API with timeout."""
    client = Groq(api_key=settings.groq_api_key)

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(TIMEOUT_SECONDS)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    raw = json.loads(response.choices[0].message.content)
    validated = InvoiceFields(**raw)
    return validated.model_dump()


def _call_gemini_fallback(text: str) -> dict:
    """Fallback to Gemini for field extraction."""
    if not settings.gemini_api_key:
        raise RuntimeError(
            "Groq rate-limited/timed out and GEMINI_API_KEY not configured"
        )

    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(
        f"{SYSTEM_PROMPT}\n\n---\n\n{text}",
        generation_config={"response_mime_type": "application/json"},
    )
    raw = json.loads(response.text)
    validated = InvoiceFields(**raw)
    return validated.model_dump()
