from fastapi import APIRouter
from app.db import get_supabase

router = APIRouter()


@router.get("/health")
async def health():
    db_ok = False
    try:
        sb = get_supabase()
        # Use a lightweight query — select from a known table with limit 0
        # This verifies both connectivity and that the schema exists
        sb.table("clients").select("id").limit(1).execute()
        db_ok = True
    except Exception:
        pass
    return {"ok": True, "db": db_ok}
