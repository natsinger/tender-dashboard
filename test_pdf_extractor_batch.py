"""Batch test: download 15 tender brochure PDFs and run the extractor on each.

Fetches recent tenders with published brochures from the API, downloads the
PDFs, and runs tender_pdf_extractor to validate extraction at scale.
"""

import json
import logging
import time
from pathlib import Path

from data_client import LandTendersClient
from tender_pdf_extractor import TenderPDFExtractor

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logging.getLogger("pdfminer").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

PDF_DIR = Path("tmp/brochures")
PDF_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_FILE = Path("tmp/batch_extraction_results.json")
NUM_TENDERS = 50


def find_tenders_with_brochures(client: LandTendersClient) -> list[dict]:
    """Find active tenders that have published brochures.

    Loads the latest snapshot and filters for active tenders with brochures.
    Then fetches detail data for each to get the document metadata.

    Args:
        client: Initialized LandTendersClient.

    Returns:
        List of dicts with tender_id and document metadata.
    """
    # Load latest snapshot
    snapshot_path = Path("data/tenders_list_11_02_2026.json")
    if not snapshot_path.exists():
        logger.error("Snapshot not found: %s", snapshot_path)
        return []

    with open(snapshot_path, "r", encoding="utf-8") as f:
        tenders = json.load(f)

    # Filter: active (status 3) + has brochure + recent (has tender types 1, 5, 8)
    candidates = [
        t
        for t in tenders
        if t.get("published_booklet") is True
        and t.get("status_code") == 3
        and t.get("tender_type_code") in (1, 5, 8)
    ]

    logger.info(
        "Found %d active tenders with brochures (types 1/5/8)", len(candidates)
    )

    # Sort by tender_id descending (most recent first)
    candidates.sort(key=lambda t: t.get("tender_id", 0), reverse=True)

    # Take the first NUM_TENDERS
    selected = candidates[:NUM_TENDERS]
    logger.info("Selected %d tenders for testing", len(selected))

    return selected


def download_brochure(
    client: LandTendersClient, tender_id: int
) -> tuple[Path | None, dict | None]:
    """Fetch tender details and download the brochure PDF.

    Args:
        client: Initialized LandTendersClient.
        tender_id: Tender ID to fetch.

    Returns:
        Tuple of (pdf_path, detail_dict) or (None, None) on failure.
    """
    pdf_path = PDF_DIR / f"{tender_id}.pdf"

    # Skip if already downloaded
    if pdf_path.exists() and pdf_path.stat().st_size > 1000:
        logger.info("Already downloaded: %s", pdf_path.name)
        return pdf_path, None

    # Fetch details
    details = client.get_tender_details_cached(tender_id)
    if not details:
        logger.warning("Could not fetch details for tender %d", tender_id)
        return None, None

    # Get the full document (brochure)
    full_doc = details.get("MichrazFullDocument", {})
    if not full_doc or not full_doc.get("MichrazID"):
        logger.warning("No MichrazFullDocument for tender %d", tender_id)
        return None, details

    # Download
    logger.info(
        "Downloading brochure for tender %d (%.1f MB)...",
        tender_id,
        full_doc.get("Size", 0) / 1024 / 1024,
    )
    content = client.download_document(full_doc)

    if not content:
        logger.warning("Download failed for tender %d", tender_id)
        return None, details

    # Save PDF
    pdf_path.write_bytes(content)
    logger.info("Saved: %s (%d bytes)", pdf_path.name, len(content))
    return pdf_path, details


def run_batch_test() -> None:
    """Main batch test: download and extract from 15 brochures."""
    client = LandTendersClient()
    extractor = TenderPDFExtractor()

    # Find tenders
    tenders = find_tenders_with_brochures(client)
    if not tenders:
        logger.error("No tenders found. Exiting.")
        return

    results = []

    for i, tender in enumerate(tenders, 1):
        tender_id = tender["tender_id"]
        logger.info(
            "--- [%d/%d] Tender %d ---", i, len(tenders), tender_id
        )

        # Download brochure
        pdf_path, details = download_brochure(client, tender_id)

        if not pdf_path:
            results.append(
                {
                    "tender_id": tender_id,
                    "tender_name": tender.get("tender_name"),
                    "city": tender.get("city"),
                    "download_success": False,
                    "extraction": None,
                }
            )
            continue

        # Run extraction
        extraction = extractor.extract(pdf_path)

        results.append(
            {
                "tender_id": tender_id,
                "tender_name": tender.get("tender_name"),
                "city": tender.get("city"),
                "type_code": tender.get("tender_type_code"),
                "download_success": True,
                "pdf_size_kb": pdf_path.stat().st_size // 1024,
                "extraction": extraction,
            }
        )

        # Rate limit
        time.sleep(0.5)

    # Save all results
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Results written to: %s", RESULTS_FILE)

    # Summary
    print("\n" + "=" * 70)
    print("BATCH EXTRACTION SUMMARY")
    print("=" * 70)

    downloaded = sum(1 for r in results if r["download_success"])
    extracted_plots = sum(
        1
        for r in results
        if r.get("extraction", {}) and r["extraction"].get("plots")
    )
    extracted_taba = sum(
        1
        for r in results
        if r.get("extraction", {}) and r["extraction"].get("taba")
    )
    extracted_purpose = sum(
        1
        for r in results
        if r.get("extraction", {}) and r["extraction"].get("purpose")
    )
    had_gush = sum(
        1
        for r in results
        if r.get("extraction", {})
        and r["extraction"].get("plots")
        and any(p.get("gush") for p in r["extraction"]["plots"])
    )

    print(f"Total tenders:    {len(results)}")
    print(f"Downloaded:       {downloaded}/{len(results)}")
    print(f"Plots found:      {extracted_plots}/{downloaded}")
    print(f"Gush found:       {had_gush}/{downloaded}")
    print(f"Taba found:       {extracted_taba}/{downloaded}")
    print(f"Purpose found:    {extracted_purpose}/{downloaded}")

    print("\nPer-tender breakdown:")
    for r in results:
        ext = r.get("extraction") or {}
        plots = ext.get("plots", [])
        gush_vals = [p.get("gush", "-") for p in plots]
        helka_vals = [p.get("helka", "-") for p in plots]
        taba = ext.get("taba", "-")
        purpose = ext.get("purpose", "-")
        status = "OK" if ext.get("success") else "FAIL"

        print(
            f"  {r['tender_id']}: {status} | "
            f"plots={len(plots)} gush={gush_vals} helka={helka_vals} | "
            f"taba={taba} | purpose={purpose}"
        )


if __name__ == "__main__":
    run_batch_test()
