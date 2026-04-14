"""History — list validated invoices, export Sage XLSX and enriched CSV."""

import re

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.db import get_supabase
from app.exporters.sage_xlsx import build_xlsx
from app.exporters.enriched_csv import build_csv
from app.jobs.weekly_recap import send_weekly_recap
from app.services.storage import signed_url

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/history")
async def history_page(
    request: Request,
    supplier_id: str | None = Query(None),
    month: str | None = Query(None),
    classification: str | None = Query(None),
):
    sb = get_supabase()

    # Fetch ALL done invoices first (unfiltered) to build filter options
    all_invoices = (
        sb.table("invoices")
        .select("*, suppliers(id, name), clients(id, code, name)")
        .eq("state", "done")
        .order("invoice_date", desc=True)
        .execute()
    ).data or []

    # Build distinct months from ALL invoices (for filter dropdown)
    all_months: list[str] = sorted(
        {inv["invoice_date"][:7] for inv in all_invoices if inv.get("invoice_date")},
        reverse=True,
    )

    # Build distinct suppliers from ALL invoices (for filter dropdown)
    all_suppliers: list[dict] = []
    seen_sup_ids: set[str] = set()
    for inv in all_invoices:
        sup = inv.get("suppliers")
        if sup and isinstance(sup, dict) and sup.get("id") and sup["id"] not in seen_sup_ids:
            seen_sup_ids.add(sup["id"])
            all_suppliers.append({"id": sup["id"], "name": sup.get("name", "")})
    all_suppliers.sort(key=lambda s: (s["name"] or "").lower())

    # Apply filters
    invoices = all_invoices
    if supplier_id:
        invoices = [inv for inv in invoices if inv.get("supplier_id") == supplier_id]
    if month and re.match(r"^\d{4}-\d{2}$", month):
        invoices = [inv for inv in invoices if inv.get("invoice_date", "").startswith(month)]
    if classification in ("auto", "manual"):
        invoices = [inv for inv in invoices if inv.get("classification") == classification]

    # Build export months from filtered results
    months: list[str] = sorted(
        {inv["invoice_date"][:7] for inv in invoices if inv.get("invoice_date")},
        reverse=True,
    )

    # All clients for dossier selector
    clients = (sb.table("clients").select("id, code, name").order("name").execute()).data or []

    # Supplier name for filter display
    filter_supplier_name = None
    if supplier_id:
        for s in all_suppliers:
            if s["id"] == supplier_id:
                filter_supplier_name = s["name"]
                break

    return templates.TemplateResponse(
        name="history.html", request=request, context={
            "active_tab": "history",
            "invoices": invoices,
            "months": months,
            "clients": clients,
            "supplier_id": supplier_id,
            "filter_supplier_name": filter_supplier_name,
            "all_months": all_months,
            "all_suppliers": all_suppliers,
            "filter_month": month or "",
            "filter_classification": classification or "",
        },
    )


@router.get("/history/export/factures_{month}.xlsx")
async def export_xlsx(month: str, dossier_client_id: str | None = Query(None)):
    if not re.match(r"^\d{4}-\d{2}$", month):
        return StreamingResponse(iter([b""]), status_code=400)
    data = build_xlsx(month, dossier_client_id)
    # Include client code in filename if filtered
    suffix = ""
    if dossier_client_id:
        sb = get_supabase()
        c = sb.table("clients").select("code").eq("id", dossier_client_id).single().execute()
        if c.data:
            suffix = f"_{c.data['code']}"
    filename = f"factures_{month}{suffix}.xlsx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/history/export/enriched_{month}.csv")
async def export_csv(month: str, dossier_client_id: str | None = Query(None)):
    if not re.match(r"^\d{4}-\d{2}$", month):
        return StreamingResponse(iter([b""]), status_code=400)
    data = build_csv(month, dossier_client_id)
    suffix = ""
    if dossier_client_id:
        sb = get_supabase()
        c = sb.table("clients").select("code").eq("id", dossier_client_id).single().execute()
        if c.data:
            suffix = f"_{c.data['code']}"
    filename = f"enriched_{month}{suffix}.csv"
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/history/pdf-url")
async def pdf_url(path: str = Query(...)):
    """Return signed URL for a PDF — used by the template."""
    url = signed_url(path)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url)
