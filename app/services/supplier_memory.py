"""Supplier memory — bump invoice count and last_seen on auto-classification."""

from datetime import datetime, timezone

from app.db import get_supabase


def upsert_and_bump(supplier_id: str) -> None:
    """Increment invoices_count and update last_seen for a known supplier."""
    sb = get_supabase()
    row = (
        sb.table("suppliers")
        .select("invoices_count")
        .eq("id", supplier_id)
        .single()
        .execute()
    )
    current_count = row.data.get("invoices_count", 0) if row.data else 0
    sb.table("suppliers").update({
        "invoices_count": current_count + 1,
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }).eq("id", supplier_id).execute()
