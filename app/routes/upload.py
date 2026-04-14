"""Upload routes — drop zone, batch processing, HTMX polling."""

import uuid

from fastapi import APIRouter, Request, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates

from app.db import get_supabase
from app.services.storage import put_inbox
from app.pipeline.orchestrator import process_invoice

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MAX_FILES = 5


@router.get("/upload")
async def upload_page(request: Request):
    sb = get_supabase()
    # Fetch recent invoices for the batch view (last 20)
    resp = (
        sb.table("invoices")
        .select("*")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    invoices = resp.data or []
    processing_count = sum(1 for i in invoices if i.get("state") in ("pending", "processing"))
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "active_tab": "upload",
        "invoices": invoices,
        "processing_count": processing_count,
    })


@router.post("/upload")
async def upload_files(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files allowed")

    sb = get_supabase()
    created_invoices = []

    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Only PDF files accepted: {f.filename}")

        pdf_bytes = await f.read()
        invoice_id = str(uuid.uuid4())

        # Insert invoice record
        sb.table("invoices").insert({
            "id": invoice_id,
            "filename": f.filename,
            "state": "pending",
        }).execute()

        # Upload to storage inbox
        put_inbox(invoice_id, pdf_bytes)

        # Queue background processing
        background_tasks.add_task(process_invoice, invoice_id)

        # Fetch the created row
        row = sb.table("invoices").select("*").eq("id", invoice_id).single().execute()
        created_invoices.append(row.data)

    return templates.TemplateResponse("partials/batch_rows.html", {
        "request": request,
        "invoices": created_invoices,
    })


@router.get("/invoices/{invoice_id}/status")
async def invoice_status(request: Request, invoice_id: str):
    sb = get_supabase()
    resp = sb.table("invoices").select("*").eq("id", invoice_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return templates.TemplateResponse("partials/batch_row.html", {
        "request": request,
        "invoice": resp.data,
    })


@router.get("/batch/status")
async def batch_status(request: Request):
    sb = get_supabase()
    resp = (
        sb.table("invoices")
        .select("*")
        .in_("state", ["pending", "processing"])
        .execute()
    )
    processing_count = len(resp.data) if resp.data else 0
    return templates.TemplateResponse("partials/batch_banner.html", {
        "request": request,
        "processing_count": processing_count,
    })


@router.post("/invoices/{invoice_id}/retry")
async def retry_invoice(
    request: Request,
    invoice_id: str,
    background_tasks: BackgroundTasks,
):
    sb = get_supabase()
    resp = sb.table("invoices").select("*").eq("id", invoice_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Reset state
    sb.table("invoices").update({
        "state": "pending",
        "state_reason": None,
    }).eq("id", invoice_id).execute()

    background_tasks.add_task(process_invoice, invoice_id)

    # Return updated row
    row = sb.table("invoices").select("*").eq("id", invoice_id).single().execute()
    return templates.TemplateResponse("partials/batch_row.html", {
        "request": request,
        "invoice": row.data,
    })
