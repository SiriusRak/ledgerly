"""Keep-alive — ping /health + SELECT 1 to prevent Render cold start and Supabase 7-day pause."""

import logging

import httpx

from app.config import settings
from app.db import get_supabase

logger = logging.getLogger(__name__)


async def keepalive() -> None:
    """Ping self /health + Supabase SELECT 1."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.public_url}/health", timeout=10)
            logger.info("Keepalive ping: %s", resp.status_code)
    except Exception as e:
        logger.warning("Keepalive ping failed: %s", e)

    try:
        sb = get_supabase()
        sb.table("clients").select("id").limit(1).execute()
        logger.info("Keepalive DB check OK")
    except Exception as e:
        logger.warning("Keepalive DB check failed: %s", e)
