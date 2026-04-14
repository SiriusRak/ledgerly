"""Supabase Storage wrapper — inbox upload, supplier move, signed URLs."""

import re
import unicodedata

from app.db import get_supabase

BUCKET = "invoices"


def _ensure_bucket() -> None:
    """Create the 'invoices' bucket if it doesn't exist (idempotent)."""
    sb = get_supabase()
    try:
        sb.storage.get_bucket(BUCKET)
    except Exception:
        sb.storage.create_bucket(BUCKET, options={"public": False})


def _normalize_for_fs(name: str) -> str:
    """Normalize a supplier name for use as a filesystem-safe path component."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9_-]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


def put_inbox(invoice_id: str, pdf_bytes: bytes) -> str:
    """Upload PDF to _inbox/{invoice_id}.pdf. Returns storage path."""
    _ensure_bucket()
    path = f"_inbox/{invoice_id}.pdf"
    sb = get_supabase()
    sb.storage.from_(BUCKET).upload(
        path, pdf_bytes, {"content-type": "application/pdf"}
    )
    return path


def get_inbox_bytes(invoice_id: str) -> bytes:
    """Download PDF bytes from _inbox/{invoice_id}.pdf."""
    sb = get_supabase()
    path = f"_inbox/{invoice_id}.pdf"
    return sb.storage.from_(BUCKET).download(path)


def move_to_supplier(
    invoice_id: str, supplier_name: str, invoice_date: str, amount_ttc: float
) -> str:
    """Move PDF from _inbox to supplier folder. Returns new path."""
    sb = get_supabase()
    supplier_dir = _normalize_for_fs(supplier_name)
    month = invoice_date[:7] if invoice_date else "unknown"
    new_path = f"{supplier_dir}/{month}_{supplier_dir}_{amount_ttc:.2f}.pdf"

    # Download then re-upload (Supabase Storage has no server-side move)
    data = sb.storage.from_(BUCKET).download(f"_inbox/{invoice_id}.pdf")
    sb.storage.from_(BUCKET).upload(
        new_path, data, {"content-type": "application/pdf"}
    )
    sb.storage.from_(BUCKET).remove([f"_inbox/{invoice_id}.pdf"])
    return new_path


def signed_url(path: str, expires_in: int = 3600) -> str:
    """Generate a signed URL for a stored PDF."""
    sb = get_supabase()
    resp = sb.storage.from_(BUCKET).create_signed_url(path, expires_in)
    return resp.get("signedURL") or resp.get("signedUrl", "")
