from __future__ import annotations


def classify(
    fields: dict,
    supplier: dict | None,
    duplicate: dict | None,
    dossier_client_id: str | None = None,
) -> tuple[str, str | None]:
    if duplicate is not None:
        inv_num = duplicate.get("invoice_number", "?")
        return ("duplicate", f"Duplicate of invoice {inv_num}")

    if supplier is None:
        return ("review", "New supplier")

    if not dossier_client_id:
        return ("review", "Unknown client")

    ht = float(fields.get("amount_ht") or 0)
    tva = float(fields.get("amount_tva") or 0)
    ttc = float(fields.get("amount_ttc") or 0)
    if abs(ht + tva - ttc) > 0.02:
        return ("review", f"VAT mismatch: {ht}+{tva}!={ttc}")

    return ("auto", None)
