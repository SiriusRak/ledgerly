"""Smoke test for the extraction pipeline (pdfplumber + Groq)."""

import json
import os

import pytest

from app.pipeline.extractor import extract_text
from app.pipeline.llm import extract_fields

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "invoice_edf_synthetic.pdf"
)


def test_extract_text_pdfplumber():
    with open(FIXTURE_PATH, "rb") as f:
        pdf_bytes = f.read()

    text, source = extract_text(pdf_bytes)
    assert source == "pdfplumber"
    assert "EDF" in text
    print(f"\n--- Extracted text (first 500 chars) ---\n{text[:500]}")


def test_extract_fields_groq():
    with open(FIXTURE_PATH, "rb") as f:
        pdf_bytes = f.read()

    text, _ = extract_text(pdf_bytes)
    fields = extract_fields(text)

    print(f"\n--- Extracted fields ---\n{json.dumps(fields, indent=2, ensure_ascii=False)}")

    assert "EDF" in fields["supplier_name"].upper()
    assert fields["siret"] == "552081317"
    assert fields["amount_ht"] == pytest.approx(100.00, abs=0.02)
    assert fields["amount_tva"] == pytest.approx(20.00, abs=0.02)
    assert fields["amount_ttc"] == pytest.approx(120.00, abs=0.02)
