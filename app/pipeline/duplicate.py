from __future__ import annotations

from app.db import get_supabase


def _fetch_candidates(supplier_id: str, fields: dict, db) -> list[dict]:
    """Fetch invoice rows that could be duplicates. Extracted for testability."""
    invoice_number = fields.get("invoice_number")
    amount_ttc = fields.get("amount_ttc")
    invoice_date = fields.get("invoice_date")

    query = (
        db.table("invoices")
        .select("*")
        .eq("supplier_id", supplier_id)
        .neq("state", "error")
    )
    resp = query.execute()

    candidates = []
    for row in resp.data:
        if row.get("invoice_number") == invoice_number:
            candidates.append(row)
            continue
        if amount_ttc is not None and invoice_date is not None:
            row_ttc = row.get("amount_ttc")
            row_date = row.get("invoice_date")
            if row_ttc is not None and row_date is not None:
                from datetime import date as date_type

                if isinstance(invoice_date, str):
                    d1 = date_type.fromisoformat(invoice_date)
                else:
                    d1 = invoice_date
                if isinstance(row_date, str):
                    d2 = date_type.fromisoformat(row_date)
                else:
                    d2 = row_date

                if abs(float(row_ttc) - float(amount_ttc)) < 0.01 and abs((d1 - d2).days) <= 7:
                    candidates.append(row)
    return candidates


def find_duplicate(
    fields: dict,
    supplier_id: str | None,
    *,
    db=None,
    _fetch=None,
) -> dict | None:
    if supplier_id is None:
        return None

    db = db or get_supabase()
    fetch = _fetch or _fetch_candidates
    candidates = fetch(supplier_id, fields, db)
    return candidates[0] if candidates else None
