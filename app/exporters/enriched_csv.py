"""Enriched CSV export — UTF-8 BOM, partie double + extra columns."""

import csv
from io import StringIO

from app.db import get_supabase
from app.exporters.sage_xlsx import _fmt_date, _fmt_mois

HEADERS = [
    "Compte", "Date", "Journal", "N\u00b0Piece", "R\u00e9f\u00e9rence",
    "Tiers", "Libell\u00e9s", "Lettrage", "D\u00e9bit", "Cr\u00e9dit",
    "Solde", "Mois", "Observation",
    "Dossier client", "SIRET", "Classification",
]


def build_csv(month: str, dossier_client_id: str | None = None) -> bytes:
    """Build enriched CSV for a given month (YYYY-MM), optionally filtered by dossier client."""
    sb = get_supabase()
    start = f"{month}-01"
    y, m = int(month[:4]), int(month[5:7])
    end = f"{y + 1}-01-01" if m == 12 else f"{y}-{m + 1:02d}-01"

    q = (
        sb.table("invoices")
        .select("*, suppliers(name, siret), clients(code)")
        .eq("state", "done")
        .gte("invoice_date", start)
        .lt("invoice_date", end)
        .order("invoice_date")
    )
    if dossier_client_id:
        q = q.eq("dossier_client_id", dossier_client_id)

    rows = q.execute().data or []

    buf = StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(HEADERS)

    for inv in rows:
        supplier_name = ""
        siret = ""
        if inv.get("suppliers") and isinstance(inv["suppliers"], dict):
            supplier_name = inv["suppliers"].get("name", "")
            siret = inv["suppliers"].get("siret", "") or ""
        if not supplier_name:
            supplier_name = inv.get("supplier_name_raw", "")
        if not siret:
            siret = inv.get("siret", "") or ""

        dossier = ""
        if inv.get("clients") and isinstance(inv["clients"], dict):
            dossier = inv["clients"].get("code", "") or ""

        classification = inv.get("classification", "") or ""
        date_str = _fmt_date(inv.get("invoice_date"))
        mois_str = _fmt_mois(inv.get("invoice_date"))
        piece = inv.get("invoice_number", "")
        libelle = f"{supplier_name} - {piece}" if piece else supplier_name
        compte_charge = inv.get("compte") or "606"
        amount_ht = float(inv.get("amount_ht") or 0)
        amount_tva = float(inv.get("amount_tva") or 0)
        amount_ttc = float(inv.get("amount_ttc") or 0)

        extra = [dossier, siret, classification]

        # Charge line
        writer.writerow([
            compte_charge, date_str, "HA", piece, "",
            supplier_name, libelle, "", f"{amount_ht:.2f}", "",
            "", mois_str, "",
        ] + extra)

        # TVA line
        if amount_tva > 0:
            writer.writerow([
                "44566", date_str, "HA", piece, "",
                supplier_name, libelle, "", f"{amount_tva:.2f}", "",
                "", mois_str, "",
            ] + extra)

        # Fournisseur line
        writer.writerow([
            "401", date_str, "HA", piece, "",
            supplier_name, libelle, "", "", f"{amount_ttc:.2f}",
            "", mois_str, "",
        ] + extra)

    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")
