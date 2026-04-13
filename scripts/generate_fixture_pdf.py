"""Generate a synthetic French invoice PDF for testing."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "invoice_edf_synthetic.pdf")


def generate():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    c = canvas.Canvas(OUTPUT, pagesize=A4)
    w, h = A4

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, h - 2 * cm, "EDF SA")
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, h - 2.8 * cm, "22-30 Avenue de Wagram, 75008 Paris")
    c.drawString(2 * cm, h - 3.4 * cm, "SIRET : 552081317")
    c.drawString(2 * cm, h - 4.0 * cm, "TVA Intracom : FR 03 552 081 317")

    # Invoice info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(12 * cm, h - 2 * cm, "FACTURE")
    c.setFont("Helvetica", 10)
    c.drawString(12 * cm, h - 2.8 * cm, "N. : FAC-2026-0001")
    c.drawString(12 * cm, h - 3.4 * cm, "Date : 15/03/2026")
    c.drawString(12 * cm, h - 4.0 * cm, "Echeance : 15/04/2026")

    # Client
    c.setFont("Helvetica-Bold", 10)
    c.drawString(12 * cm, h - 5.2 * cm, "Client : Cabinet Comptable Dupont")
    c.setFont("Helvetica", 9)
    c.drawString(12 * cm, h - 5.8 * cm, "14 rue des Lilas, 69003 Lyon")

    # Noise: delivery info
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(2 * cm, h - 6.5 * cm, "Ref. contrat : ELEC-2025-78432 / Point de livraison : 09876543210987")
    c.drawString(2 * cm, h - 7.0 * cm, "Consommation estimee : 450 kWh (periode du 01/02/2026 au 28/02/2026)")

    # Table header
    y = h - 8.5 * cm
    c.setFont("Helvetica-Bold", 9)
    for col, text in [(2, "Description"), (10, "Qte"), (12, "PU HT"), (15, "Montant HT")]:
        c.drawString(col * cm, y, text)
    c.line(2 * cm, y - 0.2 * cm, 18 * cm, y - 0.2 * cm)

    # Noise: partial subtotal line
    y -= 0.8 * cm
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, "Sous-total periode precedente (report)")
    c.drawRightString(17 * cm, y, "0.00")

    # Main line item
    y -= 0.7 * cm
    c.drawString(2 * cm, y, "Abonnement electricite mars 2026")
    c.drawString(10.5 * cm, y, "1")
    c.drawRightString(14 * cm, y, "100.00")
    c.drawRightString(17 * cm, y, "100.00")

    # Noise: another partial
    y -= 0.7 * cm
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(2 * cm, y, "Dont contribution au service public de l'electricite : 3.12 EUR (inclus)")

    # Noise: acompte line
    y -= 0.7 * cm
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, "Acompte verse le 01/03/2026")
    c.drawRightString(17 * cm, y, "-0.00")

    # Totals
    y -= 1.2 * cm
    c.line(10 * cm, y + 0.3 * cm, 18 * cm, y + 0.3 * cm)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(10 * cm, y, "Total HT")
    c.drawRightString(17 * cm, y, "100.00")

    y -= 0.6 * cm
    c.drawString(10 * cm, y, "TVA 20%")
    c.drawRightString(17 * cm, y, "20.00")

    y -= 0.6 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(10 * cm, y, "Total TTC")
    c.drawRightString(17 * cm, y, "120.00 EUR")

    # Footer noise
    y -= 1.5 * cm
    c.setFont("Helvetica", 7)
    c.drawString(2 * cm, y, "Conditions de paiement : prelevement automatique sous 30 jours.")
    y -= 0.4 * cm
    c.drawString(2 * cm, y, "En cas de retard de paiement, une penalite de 3x le taux d'interet legal sera appliquee.")
    y -= 0.4 * cm
    c.drawString(2 * cm, y, "Indemnite forfaitaire pour frais de recouvrement : 40 EUR (art. D.441-5 C. com.)")

    c.save()
    print(f"Generated: {os.path.abspath(OUTPUT)}")


if __name__ == "__main__":
    generate()
