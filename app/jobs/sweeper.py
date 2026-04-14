"""Sweeper — mark stale processing/pending invoices as error after 5 minutes."""

import logging
from datetime import datetime, timedelta, timezone

from app.db import get_supabase

logger = logging.getLogger(__name__)


async def sweep_stale() -> None:
    """Mark orphaned processing/pending invoices older than 5 min as error."""
    sb = get_supabase()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    # Pending invoices older than 5 min
    resp = (
        sb.table("invoices")
        .update({"state": "error", "state_reason": "Server restart (timeout)"})
        .eq("state", "pending")
        .lt("uploaded_at", cutoff)
        .execute()
    )
    count = len(resp.data) if resp.data else 0

    # Processing invoices without state_reason (not in review) older than 5 min
    resp2 = (
        sb.table("invoices")
        .update({"state": "error", "state_reason": "Server restart (timeout)"})
        .eq("state", "processing")
        .is_("state_reason", "null")
        .lt("uploaded_at", cutoff)
        .execute()
    )
    count += len(resp2.data) if resp2.data else 0

    if count:
        logger.info("Sweeper marked %d stale invoices as error", count)
