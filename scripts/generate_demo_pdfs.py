"""Generate 8 scripted demo PDF invoices for the Ledgerly demo."""

import os
import copy
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "demo-pdfs")

W, H = A4


# ---------------------------------------------------------------------------
# Shared drawing helpers
# ---------------------------------------------------------------------------

def draw_header(c, supplier_name, supplier_address, siret, tva_intra):
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, H - 2 * cm, supplier_name)
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, H - 2.7 * cm, supplier_address)
    c.drawString(2 * cm, H - 3.2 * cm, f"SIRET : {siret}")
    c.drawString(2 * cm, H - 3.7 * cm, f"TVA Intracom : {tva_intra}")


def draw_invoice_info(c, number, date, due_date):
    c.setFont("Helvetica-Bold", 14)
    c.drawString(12 * cm, H - 2 * cm, "FACTURE")
    c.setFont("Helvetica", 10)
    c.drawString(12 * cm, H - 2.8 * cm, f"N. : {number}")
    c.drawString(12 * cm, H - 3.4 * cm, f"Date : {date}")
    c.drawString(12 * cm, H - 4.0 * cm, f"Echeance : {due_date}")


def draw_client(c, client_name, client_address):
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12 * cm, H - 5.2 * cm, f"Client : {client_name}")
    c.setFont("Helvetica", 9)
    c.drawString(12 * cm, H - 5.8 * cm, client_address)


def draw_line_items(c, items, start_y=None):
    """Draw a table of line items. Returns y position after the table."""
    y = start_y or (H - 7.5 * cm)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(2 * cm, y, "Description")
    c.drawString(10.5 * cm, y, "Qte")
    c.drawString(12.5 * cm, y, "PU HT")
    c.drawRightString(17 * cm, y, "Montant HT")
    c.line(2 * cm, y - 0.2 * cm, 18 * cm, y - 0.2 * cm)

    y -= 0.8 * cm
    c.setFont("Helvetica", 9)
    for desc, qty, pu in items:
        montant = qty * pu
        c.drawString(2 * cm, y, desc)
        c.drawString(10.5 * cm, y, str(qty))
        c.drawRightString(14 * cm, y, f"{pu:.2f}")
        c.drawRightString(17 * cm, y, f"{montant:.2f}")
        y -= 0.6 * cm
    return y


def draw_totals(c, total_ht, tva_rate, total_tva, total_ttc, y=None):
    """Draw totals block."""
    if y is None:
        y = H - 14 * cm
    y -= 0.5 * cm
    c.line(10 * cm, y + 0.3 * cm, 18 * cm, y + 0.3 * cm)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(10 * cm, y, "Total HT")
    c.drawRightString(17 * cm, y, f"{total_ht:.2f} EUR")
    y -= 0.6 * cm
    c.drawString(10 * cm, y, f"TVA {tva_rate:.0f}%")
    c.drawRightString(17 * cm, y, f"{total_tva:.2f} EUR")
    y -= 0.6 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(10 * cm, y, "Total TTC")
    c.drawRightString(17 * cm, y, f"{total_ttc:.2f} EUR")
    return y


def draw_payment_footer(c, y=None, bank_info=None):
    if y is None:
        y = H - 17 * cm
    y -= 1.2 * cm
    c.setFont("Helvetica", 7)
    c.drawString(2 * cm, y, "Conditions de paiement : virement sous 30 jours.")
    y -= 0.4 * cm
    c.drawString(2 * cm, y, "En cas de retard, penalite de 3x le taux d'interet legal. Indemnite de recouvrement : 40 EUR.")
    if bank_info:
        y -= 0.6 * cm
        c.setFont("Helvetica", 8)
        for line in bank_info:
            c.drawString(2 * cm, y, line)
            y -= 0.4 * cm
    return y


# ---------------------------------------------------------------------------
# Invoice definitions
# ---------------------------------------------------------------------------

def gen_01_edf_001():
    """EDF first invoice — new supplier, to review."""
    path = os.path.join(OUTPUT_DIR, "01_EDF_FAC-2024-001.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    draw_header(c, "EDF SA", "22-30 Avenue de Wagram, 75008 Paris",
                "55208131766522", "FR 03 552 081 317")
    draw_invoice_info(c, "FAC-2024-001", "15/01/2024", "15/02/2024")
    draw_client(c, "Cabinet Dupont Immobilier", "14 rue des Lilas, 69003 Lyon")
    items = [
        ("Abonnement electricite janvier 2024", 1, 85.00),
        ("Consommation 420 kWh", 1, 63.00),
    ]
    y = draw_line_items(c, items)
    total_ht = 148.00
    tva = 29.60
    draw_totals(c, total_ht, 20, tva, total_ht + tva, y)
    draw_payment_footer(c)
    c.save()
    print(f"  Generated: {path}")


def gen_02_edf_002():
    """EDF second invoice — learning effect after validation."""
    path = os.path.join(OUTPUT_DIR, "02_EDF_FAC-2024-002.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    draw_header(c, "EDF SA", "22-30 Avenue de Wagram, 75008 Paris",
                "55208131766522", "FR 03 552 081 317")
    draw_invoice_info(c, "FAC-2024-002", "15/02/2024", "15/03/2024")
    draw_client(c, "Cabinet Dupont Immobilier", "14 rue des Lilas, 69003 Lyon")
    items = [
        ("Abonnement electricite fevrier 2024", 1, 85.00),
        ("Consommation 390 kWh", 1, 58.50),
    ]
    y = draw_line_items(c, items)
    total_ht = 143.50
    tva = 28.70
    draw_totals(c, total_ht, 20, tva, total_ht + tva, y)
    draw_payment_footer(c)
    c.save()
    print(f"  Generated: {path}")


def gen_03_edf_003():
    """EDF third invoice — auto-classify again."""
    path = os.path.join(OUTPUT_DIR, "03_EDF_FAC-2024-003.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    draw_header(c, "EDF SA", "22-30 Avenue de Wagram, 75008 Paris",
                "55208131766522", "FR 03 552 081 317")
    draw_invoice_info(c, "FAC-2024-003", "15/03/2024", "15/04/2024")
    draw_client(c, "Cabinet Dupont Immobilier", "14 rue des Lilas, 69003 Lyon")
    items = [
        ("Abonnement electricite mars 2024", 1, 85.00),
        ("Consommation 510 kWh", 1, 76.50),
    ]
    y = draw_line_items(c, items)
    total_ht = 161.50
    tva = 32.30
    draw_totals(c, total_ht, 20, tva, total_ht + tva, y)
    draw_payment_footer(c)
    c.save()
    print(f"  Generated: {path}")


def gen_04_plomberie():
    """Plomberie Martin — new supplier, clean extraction."""
    path = os.path.join(OUTPUT_DIR, "04_Plomberie_Martin_FAC-2024-010.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    draw_header(c, "Plomberie Martin", "8 rue du Commerce, 33000 Bordeaux",
                "84726351900014", "FR 47 847 263 519")
    draw_invoice_info(c, "FAC-2024-010", "22/01/2024", "22/02/2024")
    draw_client(c, "Martin Conseil SARL", "45 boulevard Haussmann, 75009 Paris")
    items = [
        ("Remplacement chauffe-eau 200L", 1, 450.00),
        ("Main d'oeuvre installation", 3, 55.00),
        ("Raccords cuivre et joints", 1, 32.50),
    ]
    y = draw_line_items(c, items)
    total_ht = 450.00 + 165.00 + 32.50  # 647.50
    tva = 129.50
    draw_totals(c, total_ht, 20, tva, total_ht + tva, y)
    draw_payment_footer(c)
    c.save()
    print(f"  Generated: {path}")


def gen_05_garage_vat_mismatch():
    """Garage Central — intentional VAT mismatch."""
    path = os.path.join(OUTPUT_DIR, "05_Garage_Central_FAC-2024-055.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    draw_header(c, "Garage Central SARL", "12 avenue de la Republique, 31000 Toulouse",
                "91234567800023", "FR 82 912 345 678")
    draw_invoice_info(c, "FAC-2024-055", "10/02/2024", "10/03/2024")
    draw_client(c, "Leroy Batiment SAS", "7 impasse des Artisans, 31400 Toulouse")
    items = [
        ("Vidange + filtres vehicule utilitaire", 1, 120.00),
        ("Remplacement plaquettes de frein AV", 1, 185.00),
        ("Main d'oeuvre mecanique", 2, 65.00),
    ]
    y = draw_line_items(c, items)
    # Correct HT = 120 + 185 + 130 = 435.00
    # Correct TVA 20% = 87.00 -> TTC = 522.00
    # We intentionally write wrong TTC: 525.50 (mismatch of 3.50)
    total_ht = 435.00
    tva_displayed = 87.00
    ttc_wrong = 525.50  # intentional mismatch
    draw_totals(c, total_ht, 20, tva_displayed, ttc_wrong, y)
    draw_payment_footer(c)
    c.save()
    print(f"  Generated: {path}")


def gen_06_edf_duplicate():
    """Exact copy of #1 — duplicate detection test."""
    path = os.path.join(OUTPUT_DIR, "06_EDF_FAC-2024-001_dup.pdf")
    c = canvas.Canvas(path, pagesize=A4)
    draw_header(c, "EDF SA", "22-30 Avenue de Wagram, 75008 Paris",
                "55208131766522", "FR 03 552 081 317")
    draw_invoice_info(c, "FAC-2024-001", "15/01/2024", "15/02/2024")
    draw_client(c, "Cabinet Dupont Immobilier", "14 rue des Lilas, 69003 Lyon")
    items = [
        ("Abonnement electricite janvier 2024", 1, 85.00),
        ("Consommation 420 kWh", 1, 63.00),
    ]
    y = draw_line_items(c, items)
    total_ht = 148.00
    tva = 29.60
    draw_totals(c, total_ht, 20, tva, total_ht + tva, y)
    draw_payment_footer(c)
    c.save()
    print(f"  Generated: {path}")


def gen_07_rib():
    """Bank RIB document — NOT an invoice."""
    path = os.path.join(OUTPUT_DIR, "07_RIB_BanquePopulaire.pdf")
    c = canvas.Canvas(path, pagesize=A4)

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(W / 2, H - 3 * cm, "RELEVE D'IDENTITE BANCAIRE")

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, H - 4.5 * cm, "Banque Populaire Occitane")

    y = H - 6 * cm
    c.setFont("Helvetica", 10)
    rib_fields = [
        ("Titulaire du compte", "Leroy Batiment SAS"),
        ("Code banque", "10907"),
        ("Code guichet", "00064"),
        ("Numero de compte", "02119470501"),
        ("Cle RIB", "36"),
        ("IBAN", "FR76 1090 7000 6402 1194 7050 136"),
        ("BIC / SWIFT", "CCBPFRPPNAN"),
        ("Domiciliation", "BP OCCITANE TOULOUSE CENTRE"),
    ]
    for label, value in rib_fields:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(3 * cm, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(9 * cm, y, value)
        y -= 0.7 * cm

    y -= 1 * cm
    c.setFont("Helvetica", 8)
    c.drawString(3 * cm, y, "Ce document est confidentiel. Il est destine exclusivement au titulaire du compte.")

    c.save()
    print(f"  Generated: {path}")


def gen_08_orange_multipage():
    """Orange telecom invoice — 4 pages, new supplier."""
    path = os.path.join(OUTPUT_DIR, "08_Orange_FAC-2024-100.pdf")
    c = canvas.Canvas(path, pagesize=A4)

    # --- Page 1: Header + summary ---
    draw_header(c, "Orange SA", "78 rue Olivier de Serres, 75015 Paris",
                "38012986600160", "FR 89 380 129 866")
    draw_invoice_info(c, "FAC-2024-100", "01/03/2024", "31/03/2024")
    draw_client(c, "Cabinet Dupont Immobilier", "14 rue des Lilas, 69003 Lyon")

    y = H - 7.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Recapitulatif de votre facture")
    y -= 1 * cm
    c.setFont("Helvetica", 9)
    summary_lines = [
        "Forfait Open Pro 5G  . . . . . . . . . . . . . . . 49.99 EUR HT",
        "Lignes fixes (3 postes)  . . . . . . . . . . . . . 29.97 EUR HT",
        "Options et services  . . . . . . . . . . . . . . .  5.00 EUR HT",
        "Communications hors forfait  . . . . . . . . . . . 12.40 EUR HT",
    ]
    for line in summary_lines:
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm

    y -= 0.5 * cm
    total_ht = 97.36
    tva = 19.47
    ttc = total_ht + tva  # 116.83
    draw_totals(c, total_ht, 20, tva, ttc, y)
    draw_payment_footer(c)
    c.showPage()

    # --- Page 2: Detail forfait ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, H - 2 * cm, "Detail — Forfait Open Pro 5G")
    c.setFont("Helvetica", 9)
    y = H - 3.5 * cm
    details_p2 = [
        "Ligne 06 12 34 56 78 — Forfait mensuel Open Pro 5G",
        "  Appels illimites France et Europe",
        "  Data 100 Go / mois",
        "  Engagement 24 mois (mois 14/24)",
        "",
        "Sous-total forfait : 49.99 EUR HT",
    ]
    for line in details_p2:
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm
    c.showPage()

    # --- Page 3: Detail lignes fixes ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, H - 2 * cm, "Detail — Lignes fixes")
    c.setFont("Helvetica", 9)
    y = H - 3.5 * cm
    fixed_lines = [
        ("04 78 00 11 22", "Ligne fixe standard", "9.99"),
        ("04 78 00 11 23", "Ligne fixe standard", "9.99"),
        ("04 78 00 11 24", "Ligne fixe standard", "9.99"),
    ]
    for num, desc, price in fixed_lines:
        c.drawString(2 * cm, y, f"{num} — {desc} : {price} EUR HT")
        y -= 0.5 * cm
    y -= 0.5 * cm
    c.drawString(2 * cm, y, "Sous-total lignes fixes : 29.97 EUR HT")
    y -= 1.5 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Detail — Options et services")
    y -= 1 * cm
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, "Pack Securite Pro : 5.00 EUR HT")
    c.showPage()

    # --- Page 4: Hors forfait + legal ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, H - 2 * cm, "Detail — Communications hors forfait")
    c.setFont("Helvetica", 9)
    y = H - 3.5 * cm
    hf_lines = [
        "02/03 09:14  06 98 76 54 32  3 min 22 s  0.00 EUR (inclus forfait)",
        "05/03 14:02  +41 22 123 4567  7 min 10 s  4.20 EUR",
        "12/03 10:45  +44 20 7946 0958  5 min 30 s  3.30 EUR",
        "18/03 16:30  08 99 12 34 56  12 min 00 s  4.90 EUR (surtaxe)",
    ]
    for line in hf_lines:
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm
    y -= 0.5 * cm
    c.drawString(2 * cm, y, "Sous-total hors forfait : 12.40 EUR HT")

    y -= 2 * cm
    c.setFont("Helvetica", 7)
    c.drawString(2 * cm, y, "Orange SA — Capital social 10 640 226 396 EUR — RCS Paris 380 129 866")
    y -= 0.4 * cm
    c.drawString(2 * cm, y, "Siege social : 78 rue Olivier de Serres, 75015 Paris")

    c.save()
    print(f"  Generated: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Generating 8 demo PDFs...")
    gen_01_edf_001()
    gen_02_edf_002()
    gen_03_edf_003()
    gen_04_plomberie()
    gen_05_garage_vat_mismatch()
    gen_06_edf_duplicate()
    gen_07_rib()
    gen_08_orange_multipage()
    print("All 8 PDFs generated.")


if __name__ == "__main__":
    main()
