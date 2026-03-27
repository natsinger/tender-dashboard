"""Fetch Taba plan documents via the RMI REST API (no Playwright needed).

Replaces the Playwright-based mavat_client.py with direct HTTP calls:
1. Get plan ID from tender details (MichrazDetailsApi)
2. Look up plan documents via TabaSearch API
3. Download the תקנון (takanon) PDF directly from apps.land.gov.il

The takanon PDF contains Section 5 (טבלת זכויות בנייה) which is parsed
by building_rights_extractor.py.

Usage:
    from taba_client import TabaClient

    client = TabaClient()
    result = client.download_takanon_for_tender(20250067)
    print(result)
    # {"status": "success", "plan_number": "610-0893396", "file_path": "tmp/mavat_cache/610-0893396.pdf"}

    # Or by plan ID directly:
    result = client.download_takanon_by_plan_id("6053424")
"""

import logging
import re
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# RMI API endpoints
TENDER_DETAILS_URL = (
    "https://apps.land.gov.il/MichrazimSite/api/MichrazDetailsApi/Get"
)
TABA_SEARCH_URL = (
    "https://apps.land.gov.il/TabaSearch/api//SerachPlans/GetPlans"
)
PDF_BASE_URL = "https://apps.land.gov.il"

# Request timeout in seconds
REQUEST_TIMEOUT = 30


class TabaClient:
    """Fetches Taba plan documents via RMI REST API.

    No browser automation needed — all data is available through public
    JSON APIs and direct PDF downloads.
    """

    def __init__(
        self,
        output_dir: Path | str = "tmp/mavat_cache",
    ) -> None:
        """Initialize the Taba client.

        Args:
            output_dir: Directory to save downloaded PDFs.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def get_tender_plan_ids(self, tender_id: int) -> list[dict]:
        """Extract plan IDs and Taba plan numbers from a tender's details.

        Reads TochnitMigrash from each Tik (lot) and MichrazLinks URL
        to find the plan ID and real Taba plan number.

        Args:
            tender_id: The RMI tender ID (e.g., 20250067).

        Returns:
            List of dicts with keys: plan_id, plan_number, migrash_name.
        """
        url = f"{TENDER_DETAILS_URL}?michrazID={tender_id}"
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            detail = resp.json()
        except Exception as e:
            logger.error("Failed to fetch tender %d details: %s", tender_id, e)
            return []

        plans: list[dict] = []
        seen_plan_numbers: set[str] = set()

        # Source 1: TochnitMigrash in each Tik (most reliable)
        for tik in detail.get("Tik", []):
            for tm in tik.get("TochnitMigrash", []):
                tochnit = tm.get("Tochnit", "").strip()
                if tochnit and tochnit not in seen_plan_numbers:
                    seen_plan_numbers.add(tochnit)
                    plans.append({
                        "plan_number": tochnit,
                        "plan_id": None,
                        "migrash_name": tm.get("MigrashName", "").strip(),
                    })

        # Source 2: MichrazLinks URL → extract planId
        plan_id_from_url = None
        for link in detail.get("MichrazLinks", []):
            url_str = link.get("url", "")
            match = re.search(r"planNumber=([^&,]+)", url_str)
            if match:
                plan_id_from_url = match.group(1)
                break

        # Attach plan_id to plans if we found one
        if plan_id_from_url:
            for plan in plans:
                plan["plan_id"] = plan_id_from_url
            # If no plans from TochnitMigrash, create one from the URL
            if not plans:
                plans.append({
                    "plan_number": None,
                    "plan_id": plan_id_from_url,
                    "migrash_name": None,
                })

        logger.info(
            "Tender %d: found %d plan(s), plan_id=%s",
            tender_id, len(plans), plan_id_from_url,
        )
        return plans

    def search_plan(self, plan_id: str) -> Optional[dict]:
        """Search the TabaSearch API for a plan by its ID.

        Args:
            plan_id: The plan ID (e.g., "6053424" from the MichrazLinks URL).

        Returns:
            Plan dict with planNumber, planId, documentsSet, etc., or None.
        """
        try:
            resp = self.session.post(
                TABA_SEARCH_URL,
                json={"planNumber": plan_id},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("TabaSearch API failed for plan %s: %s", plan_id, e)
            return None

        plans = data.get("plansSmall", [])
        if not plans:
            logger.warning("TabaSearch returned no plans for ID %s", plan_id)
            return None

        plan = plans[0]
        logger.info(
            "TabaSearch: plan %s → %s (%s)",
            plan_id, plan.get("planNumber"), plan.get("mahut"),
        )
        return plan

    def get_takanon_url(self, plan_data: dict) -> Optional[str]:
        """Extract the takanon (תקנון) PDF download URL from plan data.

        Args:
            plan_data: Plan dict from search_plan().

        Returns:
            Full download URL, or None if no takanon document.
        """
        docs = plan_data.get("documentsSet", {})
        takanon = docs.get("takanon")
        if not takanon or not takanon.get("path"):
            logger.warning(
                "No takanon document for plan %s",
                plan_data.get("planNumber"),
            )
            return None

        path = takanon["path"].replace("\\", "/")
        return f"{PDF_BASE_URL}{path}"

    def download_pdf(self, url: str, save_path: Path) -> bool:
        """Download a PDF from a URL.

        Args:
            url: Full URL to the PDF.
            save_path: Local path to save the file.

        Returns:
            True if download succeeded.
        """
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
            resp.raise_for_status()

            # Verify it's actually a PDF
            content_start = resp.content[:4]
            if content_start != b"%PDF":
                logger.error(
                    "URL did not return a PDF (got %s): %s",
                    resp.headers.get("content-type"), url,
                )
                return False

            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(resp.content)
            logger.info(
                "Downloaded PDF: %s (%d KB)",
                save_path.name, len(resp.content) // 1024,
            )
            return True

        except Exception as e:
            logger.error("PDF download failed: %s — %s", url, e)
            return False

    def download_takanon_by_plan_id(
        self,
        plan_id: str,
        plan_number: Optional[str] = None,
    ) -> dict:
        """Download the takanon PDF for a plan by its ID.

        Args:
            plan_id: The plan ID (e.g., "6053424").
            plan_number: Optional Taba plan number for naming the file.

        Returns:
            Result dict with keys: status, plan_number, plan_id, file_path, error.
        """
        result: dict = {
            "status": "pending",
            "plan_number": plan_number,
            "plan_id": plan_id,
            "file_path": None,
            "error": None,
        }

        # Step 1: Search TabaSearch API
        plan_data = self.search_plan(plan_id)
        if not plan_data:
            result["status"] = "not_found"
            result["error"] = f"Plan ID {plan_id} not found in TabaSearch"
            return result

        real_plan_number = plan_data.get("planNumber", plan_number or plan_id)
        result["plan_number"] = real_plan_number

        # Step 2: Get takanon URL
        pdf_url = self.get_takanon_url(plan_data)
        if not pdf_url:
            result["status"] = "no_takanon"
            result["error"] = f"No takanon document for plan {real_plan_number}"
            return result

        # Step 3: Download PDF
        safe_name = real_plan_number.replace("/", "_").replace("\\", "_")
        save_path = self.output_dir / f"{safe_name}.pdf"

        # Use cached file if it exists
        if save_path.exists() and save_path.stat().st_size > 1000:
            logger.info("Using cached PDF: %s", save_path)
            result["status"] = "success"
            result["file_path"] = str(save_path)
            return result

        if self.download_pdf(pdf_url, save_path):
            result["status"] = "success"
            result["file_path"] = str(save_path)
        else:
            result["status"] = "download_failed"
            result["error"] = f"Failed to download PDF from {pdf_url}"

        return result

    def download_takanon_for_tender(self, tender_id: int) -> dict:
        """Full pipeline: tender ID → plan lookup → takanon PDF download.

        Args:
            tender_id: The RMI tender ID (e.g., 20250067).

        Returns:
            Result dict with keys: status, tender_id, plan_number, plan_id,
            file_path, error.
        """
        result: dict = {
            "status": "pending",
            "tender_id": tender_id,
            "plan_number": None,
            "plan_id": None,
            "file_path": None,
            "error": None,
        }

        # Step 1: Get plan IDs from tender
        plans = self.get_tender_plan_ids(tender_id)
        if not plans:
            result["status"] = "no_plans"
            result["error"] = f"No plans linked to tender {tender_id}"
            return result

        plan_id = plans[0].get("plan_id")
        plan_number = plans[0].get("plan_number")
        result["plan_number"] = plan_number
        result["plan_id"] = plan_id

        if not plan_id:
            result["status"] = "no_plan_id"
            result["error"] = (
                f"Plan number {plan_number} found but no plan_id "
                "(missing MichrazLinks TabaSearch URL)"
            )
            return result

        # Step 2: Download takanon by plan ID
        download_result = self.download_takanon_by_plan_id(
            plan_id, plan_number=plan_number,
        )

        result.update({
            "status": download_result["status"],
            "plan_number": download_result["plan_number"],
            "file_path": download_result["file_path"],
            "error": download_result["error"],
        })
        return result
