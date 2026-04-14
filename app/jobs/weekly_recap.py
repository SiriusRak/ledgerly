"""Weekly recap email — Monday 8:00 Europe/Paris via Resend."""

import logging
from datetime import datetime, timedelta, timezone

import resend

from app.config import settings
from app.db import get_supabase

logger = logging.getLogger(__name__)


async def send_weekly_recap() -> dict:
    """Compute weekly stats and send recap email. Skip if 0 invoices.

    Returns dict with "status" ('sent', 'empty', 'error') and optional "message".
    """
    sb = get_supabase()

    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=7)).isoformat()

    # Fetch this week's done invoices
    resp = (
        sb.table("invoices")
        .select("*, suppliers(name)")
        .eq("state", "done")
        .gte("processed_at", week_start)
        .execute()
    )
    invoices = resp.data or []

    if not invoices:
        logger.info("Weekly recap: 0 invoices this week, skipping send")
        return {"status": "empty", "message": "No invoices to recap this week"}

    # Stats
    total = len(invoices)
    auto = sum(1 for i in invoices if i.get("classification") == "auto")
    manual = total - auto
    sum_ttc = sum(float(i.get("amount_ttc") or 0) for i in invoices)

    # Top 3 suppliers by total amount
    supplier_totals: dict[str, float] = {}
    for i in invoices:
        name = ""
        if i.get("suppliers") and isinstance(i["suppliers"], dict):
            name = i["suppliers"].get("name", "")
        name = name or i.get("supplier_name_raw", "Unknown")
        supplier_totals[name] = supplier_totals.get(name, 0) + float(i.get("amount_ttc") or 0)
    top3 = sorted(supplier_totals.items(), key=lambda x: -x[1])[:3]

    # Duplicates and errors this week
    dup_resp = (
        sb.table("invoices")
        .select("id", count="exact")
        .eq("state", "duplicate")
        .gte("uploaded_at", week_start)
        .execute()
    )
    dup_count = dup_resp.count or 0

    err_resp = (
        sb.table("invoices")
        .select("id", count="exact")
        .eq("state", "error")
        .gte("uploaded_at", week_start)
        .execute()
    )
    err_count = err_resp.count or 0

    # Week number
    week_num = now.isocalendar()[1]
    week_end = now.strftime("%b %d")
    week_begin = (now - timedelta(days=6)).strftime("%b %d")

    # Build HTML email
    month = now.strftime("%Y-%m")
    download_url = f"{settings.public_url}/history/export/factures_{month}.xlsx"

    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #4F46E5;">Ledgerly -- Week {week_num} recap ({week_begin} - {week_end})</h2>

      <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
        <tr>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Invoices processed</td>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right; font-weight: 600;">{total}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Auto-classified / Manual</td>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right;">{auto} / {manual}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Total TTC</td>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right; font-weight: 600;">{sum_ttc:,.2f} EUR</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Duplicates detected</td>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right;">{dup_count}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB;">Errors</td>
          <td style="padding: 8px 0; border-bottom: 1px solid #E5E7EB; text-align: right;">{err_count}</td>
        </tr>
      </table>

      <h3 style="margin-top: 20px;">Top 3 suppliers</h3>
      <ol style="padding-left: 20px;">
        {"".join(f'<li>{name} -- {amt:,.2f} EUR</li>' for name, amt in top3)}
      </ol>

      <div style="margin-top: 24px;">
        <a href="{download_url}"
           style="display: inline-block; background: #4F46E5; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 500;">
          Download {month} xlsx
        </a>
      </div>

      <p style="margin-top: 24px; color: #9CA3AF; font-size: 12px;">Ledgerly -- Invoice processing for accountants</p>
    </div>
    """

    # Send via Resend
    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": "Ledgerly <onboarding@resend.dev>",
            "to": [settings.recap_email],
            "subject": f"Ledgerly -- week {week_num} recap ({week_begin} - {week_end})",
            "html": html,
        })
        logger.info("Weekly recap sent to %s", settings.recap_email)
        return {"status": "sent", "message": f"Recap sent to {settings.recap_email}"}
    except Exception as e:
        logger.error("Weekly recap send failed: %s", e)
        try:
            sb.table("recap_failures").insert({
                "error": str(e)[:500],
            }).execute()
        except Exception:
            pass
        return {"status": "error", "message": str(e)[:200]}
