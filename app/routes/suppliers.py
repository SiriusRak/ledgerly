"""Suppliers — read-only list of learned suppliers."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.db import get_supabase

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/suppliers")
async def suppliers_page(request: Request):
    sb = get_supabase()
    resp = (
        sb.table("suppliers")
        .select("*, clients:default_dossier_client_id(name)")
        .order("last_seen", desc=True)
        .execute()
    )
    suppliers = resp.data or []
    return templates.TemplateResponse(
        "suppliers.html",
        {"request": request, "active_tab": "suppliers", "suppliers": suppliers},
    )
