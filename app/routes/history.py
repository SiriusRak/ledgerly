"""History — list validated invoices, export Sage XLSX and enriched CSV."""

import re

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from app.db import get_supabase
from app.exporters.sage_xlsx import build_xlsx
from app.exporters.enriched_csv import build_csv
from app.services.storage import signed_url

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/history")
async def history_page(
    request: Request,
    supplier_id: str | None = Query(None),
):
    sb = get_supabase()
    q = (
        sb.table("invoices")
        .select("*, suppliers(id, name), clients(code)")
        .eq("state", "done")
        .order("invoice_date", desc=True)
    )
    if supplier_id:
        q = q.eq("supplier_id", supplier_id)

    invoices = (q.execute()).data or []

    # Build distinct months for export selector (newest first)
    months: list[str] = sorted(
        {inv["invoice_date"][:7] for inv in invoices if inv.get("invoice_date")},
        reverse=True,
    )

    # Supplier name for filter display
    filter_supplier_name = None
    if supplier_id and invoices:
        sup = invoices[0].get("suppliers")
        if sup and isinstance(sup, dict):
            filter_supplier_name = sup.get("name")

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "active_tab": "history",
            "invoices": invoices,
            "months": months,
            "supplier_id": supplier_id,
            "filter_supplier_name": filter_supplier_name,
        },
    )


@router.get("/history/export/factures_{month}.xlsx")
async def export_xlsx(month: str):
    if not re.match(r"^\d{4}-\d{2}$", month):
        return StreamingResponse(iter([b""]), status_code=400)
    data = build_xlsx(month)
    filename = f"factures_{month}.xlsx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/history/export/enriched_{month}.csv")
async def export_csv(month: str):
    if not re.match(r"^\d{4}-\d{2}$", month):
        return StreamingResponse(iter([b""]), status_code=400)
    data = build_csv(month)
    filename = f"enriched_{month}.csv"
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
