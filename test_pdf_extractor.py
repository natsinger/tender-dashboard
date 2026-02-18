"""Test script for tender_pdf_extractor module.

Runs extraction on hoveret_1.pdf and hoverete_2.pdf, saves results to JSON,
and validates expected values.
"""

import json
import logging
from pathlib import Path

from tender_pdf_extractor import TenderPDFExtractor

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
# Suppress pdfminer debug noise
logging.getLogger("pdfminer").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("tmp")
OUTPUT_DIR.mkdir(exist_ok=True)


def run_test() -> None:
    """Run extraction on test PDFs and validate results."""
    extractor = TenderPDFExtractor()
    results = {}

    test_files = [Path("hoveret_1.pdf"), Path("hoverete_2.pdf")]

    for pdf_file in test_files:
        if not pdf_file.exists():
            logger.error("Test file not found: %s", pdf_file)
            continue

        logger.info("=" * 60)
        logger.info("Processing: %s", pdf_file.name)
        logger.info("=" * 60)

        extracted = extractor.extract(pdf_file)
        results[pdf_file.name] = extracted

    # Write results to JSON file (avoids console encoding issues)
    output_path = OUTPUT_DIR / "extraction_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Results written to: %s", output_path)

    # Validate hoveret_1.pdf expected values
    if "hoveret_1.pdf" in results:
        r = results["hoveret_1.pdf"]
        logger.info("--- Validation: hoveret_1.pdf ---")
        _check("success", r["success"], True)
        _check("taba", r["taba"], "632-1274539")
        if r["plots"]:
            plot = r["plots"][0]
            _check("gush", plot.get("gush"), "2199")
            _check("helka", plot.get("helka"), "39,40")
            _check("migrash", plot.get("migrash"), "39,40")
        else:
            logger.error("  FAIL: No plots extracted")

    # Validate hoverete_2.pdf expected values
    if "hoverete_2.pdf" in results:
        r = results["hoverete_2.pdf"]
        logger.info("--- Validation: hoverete_2.pdf ---")
        _check("success", r["success"], True)
        if r["plots"]:
            plot = r["plots"][0]
            _check("migrash", plot.get("migrash"), "951")
        else:
            logger.error("  FAIL: No plots extracted")
        # Log taba and purpose for manual inspection
        logger.info("  taba: %s", r.get("taba"))
        logger.info("  purpose: %s", r.get("purpose"))


def _check(field: str, actual: object, expected: object) -> None:
    """Log pass/fail for a field check."""
    if actual == expected:
        logger.info("  PASS: %s = %s", field, actual)
    else:
        logger.warning("  FAIL: %s = %s (expected %s)", field, actual, expected)


if __name__ == "__main__":
    run_test()
