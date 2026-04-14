"""Invoice processing orchestrator — BackgroundTask entrypoint."""

import json
import logging
from datetime import datetime, timezone

from app.db import get_supabase
from app.pipeline.extractor import extract_text
from app.pipeline.llm import extract_fields
from app.pipeline.matcher import find_supplier
from app.pipeline.duplicate import find_duplicate
from app.pipeline.confidence import classify
from app.services.storage import get_inbox_bytes, move_to_supplier
from app.services.supplier_memory import upsert_and_bump

logger = logging.getLogger(__name__)


def process_invoice(invoice_id: str) -> None:
    """Full pipeline: extract, classify, store. Called as BackgroundTask."""
    sb = get_supabase()

    try:
        # 1. Mark as processing
        sb.table("invoices").update({"state": "processing"}).eq("id", invoice_id).execute()

        # 2. Get PDF bytes
        pdf_bytes = get_inbox_bytes(invoice_id)

        # 3. Extract text
        text, source = extract_text(pdf_bytes)

        # 4. LLM field extraction
        fields = extract_fields(text)

        # 5. Save raw extraction
        sb.table("invoices").update({
            "raw_extraction": json.dumps(fields),
            "supplier_name_raw": fields.get("supplier_name"),
            "siret": fields.get("siret"),
            "invoice_date": fields.get("invoice_date"),
            "invoice_number": fields.get("invoice_number"),
            "amount_ht": fields.get("amount_ht"),
            "amount_tva": fields.get("amount_tva"),
            "amount_ttc": fields.get("amount_ttc"),
            "tva_rate": fields.get("tva_rate"),
        }).eq("id", invoice_id).execute()

        # 6. Find supplier
        supplier = find_supplier(fields)

        # 7. Check duplicates
        supplier_id = supplier["id"] if supplier else None
        duplicate = find_duplicate(fields, supplier_id)

        # 8. Classify
        status, reason = classify(fields, supplier, duplicate)

        # 9. Apply result
        if status == "duplicate":
            dup_id = duplicate["id"] if duplicate else None
            sb.table("invoices").update({
                "state": "duplicate",
                "state_reason": reason,
                "duplicate_of": dup_id,
                "supplier_id": supplier_id,
            }).eq("id", invoice_id).execute()

        elif status == "auto":
            # Move PDF to supplier folder
            storage_path = move_to_supplier(
                invoice_id,
                fields.get("supplier_name", "unknown"),
                fields.get("invoice_date", ""),
                fields.get("amount_ttc", 0.0),
            )
            update_data = {
                "state": "done",
                "classification": "auto",
                "supplier_id": supplier_id,
                "pdf_storage_path": storage_path,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "compte": supplier.get("default_compte"),
                "dossier_client_id": supplier.get("default_dossier_client_id"),
                "journal": supplier.get("default_journal", "HA"),
                "libelle": f"{supplier.get('name', '')} - {fields.get('invoice_number', '')}",
            }
            # Remove None values to avoid overwriting with null
            update_data = {k: v for k, v in update_data.items() if v is not None}
            sb.table("invoices").update(update_data).eq("id", invoice_id).execute()

            # Bump supplier memory
            if supplier_id:
                upsert_and_bump(supplier_id)

        elif status == "review":
            # Keep state='processing' with state_reason set — UI shows "To review"
            sb.table("invoices").update({
                "state": "processing",
                "state_reason": reason,
                "supplier_id": supplier_id,
            }).eq("id", invoice_id).execute()

    except Exception as e:
        logger.exception("Error processing invoice %s", invoice_id)
        sb.table("invoices").update({
            "state": "error",
            "state_reason": str(e)[:200],
        }).eq("id", invoice_id).execute()
