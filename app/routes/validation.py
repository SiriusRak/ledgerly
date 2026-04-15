"""Validation queue — list, detail split-pane, RPC validate."""

from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import get_supabase
from app.pipeline.matcher import normalize_name
from app.services.storage import move_to_supplier, signed_url

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def _reason_priority(reason: str) -> int:
    """Sort priority based on reason content (not exact match)."""
    r = reason.lower()
    if "duplicate" in r:
        return 0
    if "vat" in r or "tva" in r:
        return 1
    if "new supplier" in r or "nouveau" in r:
        return 2
    return 99


def _sort_key(inv: dict) -> tuple:
    reason = inv.get("state_reason") or ""
    return (_reason_priority(reason), inv.get("uploaded_at") or "")


@router.get("/queue")
async def queue_list(request: Request):
    sb = get_supabase()
    resp = (
        sb.table("invoices")
        .select("*")
        .eq("state", "processing")
        .not_.is_("state_reason", "null")
        .execute()
    )
    invoices = sorted(resp.data or [], key=_sort_key)
    return templates.TemplateResponse(
        name="queue.html", request=request, context={"active_tab": "queue", "invoices": invoices},
    )


@router.get("/queue/{invoice_id}")
async def queue_detail(request: Request, invoice_id: str):
    sb = get_supabase()
    inv_resp = (
        sb.table("invoices").select("*").eq("id", invoice_id).single().execute()
    )
    invoice = inv_resp.data

    # Supplier info if linked
    supplier = None
    if invoice.get("supplier_id"):
        s_resp = (
            sb.table("suppliers")
            .select("*")
            .eq("id", invoice["supplier_id"])
            .single()
            .execute()
        )
        supplier = s_resp.data

    # Clients list
    clients_resp = sb.table("clients").select("*").order("name").execute()
    clients = clients_resp.data or []

    # Signed PDF URL
    pdf_url = ""
    if invoice.get("pdf_storage_path"):
        pdf_url = signed_url(invoice["pdf_storage_path"])

    # Format date for display (YYYY-MM-DD -> DD/MM/YYYY)
    display_date = ""
    if invoice.get("invoice_date"):
        try:
            d = datetime.strptime(invoice["invoice_date"], "%Y-%m-%d")
            display_date = d.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            display_date = invoice["invoice_date"]

    # Next invoice in queue (for redirect after validate)
    queue_resp = (
        sb.table("invoices")
        .select("id, state_reason, uploaded_at")
        .eq("state", "processing")
        .not_.is_("state_reason", "null")
        .neq("id", invoice_id)
        .execute()
    )
    queue_items = sorted(queue_resp.data or [], key=_sort_key)
    next_id = queue_items[0]["id"] if queue_items else None

    return templates.TemplateResponse(
        name="validation_detail.html", request=request, context={
            "active_tab": "queue",
            "invoice": invoice,
            "supplier": supplier,
            "clients": clients,
            "pdf_url": pdf_url,
            "display_date": display_date,
            "next_id": next_id,
        },
    )


@router.post("/queue/{invoice_id}/validate")
async def validate_invoice(
    invoice_id: str,
    compte: str = Form(""),
    dossier_client_id: str = Form(""),
    journal: str = Form("HA"),
    libelle: str = Form(""),
    invoice_date: str = Form(""),
    invoice_number: str = Form(""),
    amount_ht: str = Form("0"),
    amount_tva: str = Form("0"),
    amount_ttc: str = Form("0"),
    tva_rate: str = Form("0"),
    supplier_name: str = Form(""),
    siret: str = Form(""),
):
    sb = get_supabase()

    # Parse date DD/MM/YYYY -> YYYY-MM-DD
    parsed_date = invoice_date
    if "/" in invoice_date:
        try:
            d = datetime.strptime(invoice_date.strip(), "%d/%m/%Y")
            parsed_date = d.strftime("%Y-%m-%d")
        except ValueError:
            parsed_date = invoice_date

    # Parse amounts (French format: 1 234,56 -> 1234.56)
    def parse_amount(val: str) -> float:
        v = val.replace("\u202f", "").replace("\xa0", "").replace(" ", "").replace(",", ".")
        try:
            return float(v)
        except ValueError:
            return 0.0

    ht = parse_amount(amount_ht)
    tva = parse_amount(amount_tva)
    ttc = parse_amount(amount_ttc)
    rate = parse_amount(tva_rate)

    supplier_norm = normalize_name(supplier_name) if supplier_name.strip() else ""

    # Call RPC
    sb.rpc(
        "validate_invoice",
        {
            "p_invoice_id": invoice_id,
            "p_compte": compte,
            "p_dossier_client_id": dossier_client_id or None,
            "p_journal": journal,
            "p_libelle": libelle,
            "p_invoice_date": parsed_date,
            "p_invoice_number": invoice_number,
            "p_amount_ht": ht,
            "p_amount_tva": tva,
            "p_amount_ttc": ttc,
            "p_tva_rate": rate,
            "p_supplier_name": supplier_name,
            "p_supplier_name_normalized": supplier_norm,
            "p_siret": siret,
        },
    ).execute()

    # Move PDF to supplier folder and persist new path
    try:
        new_path = move_to_supplier(invoice_id, supplier_name, parsed_date, ttc)
        sb.table("invoices").update({"pdf_storage_path": new_path}).eq("id", invoice_id).execute()
    except Exception:
        pass  # Non-blocking — PDF stays in inbox if move fails

    # Redirect to next item or back to queue
    queue_resp = (
        sb.table("invoices")
        .select("id, state_reason, uploaded_at")
        .eq("state", "processing")
        .not_.is_("state_reason", "null")
        .execute()
    )
    queue_items = sorted(queue_resp.data or [], key=_sort_key)
    if queue_items:
        return RedirectResponse(f"/queue/{queue_items[0]['id']}", status_code=303)
    return RedirectResponse("/queue", status_code=303)


@router.get("/clients/new-inline")
async def new_client_inline(request: Request):
    return templates.TemplateResponse(
        name="partials/new_client_inline.html", request=request, context={},
    )


@router.post("/clients")
async def create_client(request: Request, name: str = Form(...), code: str = Form("")):
    sb = get_supabase()
    client_code = code.strip() or name.strip().upper().replace(" ", "_")[:20]
    resp = sb.table("clients").insert({"name": name.strip(), "code": client_code}).execute()
    client = resp.data[0]
    html = f'<option value="{client["id"]}" selected>{client["name"]}</option>'
    from fastapi.responses import HTMLResponse

    return HTMLResponse(html)
