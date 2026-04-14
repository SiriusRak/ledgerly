"""Playwright async script: seed, upload 8 PDFs, validate, capture screenshots + xlsx."""

import asyncio
import glob
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"
DEMO_PDFS_DIR = os.path.join(os.path.dirname(__file__), "..", "demo-pdfs")
DEMO_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "demo-assets")

# Ordered list of PDFs to upload (order matters for the demo scenario)
PDF_FILES = [
    "01_EDF_FAC-2024-001.pdf",
    "02_EDF_FAC-2024-002.pdf",
    "03_EDF_FAC-2024-003.pdf",
    "04_Plomberie_Martin_FAC-2024-010.pdf",
    "05_Garage_Central_FAC-2024-055.pdf",
    "06_EDF_FAC-2024-001_dup.pdf",
    "07_RIB_BanquePopulaire.pdf",
    "08_Orange_FAC-2024-100.pdf",
]


async def wait_for_processing(page, timeout_s=120):
    """Poll the queue page until no invoices are in 'processing' state."""
    print("  Waiting for pipeline processing to complete...")
    start = time.time()
    while time.time() - start < timeout_s:
        await page.goto(f"{BASE_URL}/queue")
        await page.wait_for_load_state("networkidle")
        content = await page.content()
        if "processing" not in content.lower() and "en cours" not in content.lower():
            print("  Processing complete.")
            return
        await asyncio.sleep(3)
    print("  Warning: timeout waiting for processing to finish.")


async def upload_pdf(page, filepath):
    """Upload a single PDF via the /upload page."""
    await page.goto(f"{BASE_URL}/upload")
    await page.wait_for_load_state("networkidle")

    file_input = page.locator("input[type='file']")
    await file_input.set_input_files(filepath)

    # Look for a submit/upload button and click it
    submit = page.locator("button[type='submit'], button:has-text('Upload'), button:has-text('Envoyer')")
    if await submit.count() > 0:
        await submit.first.click()
        await page.wait_for_load_state("networkidle")
        # Wait a moment for HTMX to settle
        await asyncio.sleep(1)


async def validate_review_items(page):
    """Go to /queue and validate items that are in 'to review' state."""
    await page.goto(f"{BASE_URL}/queue")
    await page.wait_for_load_state("networkidle")

    # Find all links to invoice detail pages in the queue
    links = await page.locator("a[href*='/queue/']").all()
    detail_urls = []
    for link in links:
        href = await link.get_attribute("href")
        if href and "/queue/" in href:
            detail_urls.append(href if href.startswith("http") else f"{BASE_URL}{href}")

    for url in detail_urls:
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        # Look for a validate button
        validate_btn = page.locator(
            "button:has-text('Valider'), button:has-text('Validate'), "
            "button:has-text('Approuver'), button[name='action'][value='validate']"
        )
        if await validate_btn.count() > 0:
            await validate_btn.first.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(0.5)
            print(f"  Validated: {url}")


async def capture_screenshots(page):
    """Take screenshots of key pages."""
    pages_to_capture = [
        ("upload", "/upload"),
        ("queue", "/queue"),
        ("history", "/history"),
        ("suppliers", "/suppliers"),
    ]
    for name, path in pages_to_capture:
        await page.goto(f"{BASE_URL}{path}")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(0.5)
        screenshot_path = os.path.join(DEMO_ASSETS_DIR, f"{name}.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"  Screenshot: {screenshot_path}")


async def download_xlsx(page):
    """Attempt to download the XLSX export."""
    # Try /history page for an export link/button
    await page.goto(f"{BASE_URL}/history")
    await page.wait_for_load_state("networkidle")

    export_btn = page.locator(
        "a:has-text('Export'), a:has-text('XLSX'), a:has-text('Telecharger'), "
        "button:has-text('Export'), button:has-text('XLSX')"
    )
    if await export_btn.count() > 0:
        async with page.expect_download(timeout=15000) as download_info:
            await export_btn.first.click()
        download = await download_info.value
        dest = os.path.join(DEMO_ASSETS_DIR, "export.xlsx")
        await download.save_as(dest)
        print(f"  Downloaded: {dest}")
    else:
        print("  No export button found on /history, skipping XLSX download.")


async def main():
    os.makedirs(DEMO_ASSETS_DIR, exist_ok=True)

    # Step 1: Seed the database
    print("Step 1: Seeding database...")
    from scripts.seed_demo import run as seed_run
    seed_run()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # Step 2: Upload all 8 PDFs one by one
        print("Step 2: Uploading 8 demo PDFs...")
        for filename in PDF_FILES:
            filepath = os.path.join(DEMO_PDFS_DIR, filename)
            if not os.path.exists(filepath):
                print(f"  WARNING: {filepath} not found, skipping.")
                continue
            await upload_pdf(page, filepath)
            print(f"  Uploaded: {filename}")
            # Small delay between uploads to let pipeline start
            await asyncio.sleep(1)

        # Step 3: Wait for processing
        print("Step 3: Waiting for processing...")
        await wait_for_processing(page)

        # Step 4: Validate review items
        print("Step 4: Validating review items in queue...")
        await validate_review_items(page)

        # Step 5: Wait again for any re-processing after validation
        await asyncio.sleep(3)

        # Step 6: Capture screenshots
        print("Step 5: Capturing screenshots...")
        await capture_screenshots(page)

        # Step 7: Download XLSX
        print("Step 6: Downloading XLSX export...")
        await download_xlsx(page)

        await browser.close()

    print("Demo capture complete. Artifacts in demo-assets/")


if __name__ == "__main__":
    asyncio.run(main())
