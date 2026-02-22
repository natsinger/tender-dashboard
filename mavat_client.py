"""Fetch zoning plan documents (הוראות התכנית) from mavat.iplan.gov.il.

Uses Playwright browser automation to search for plans by תב"ע number and
download their instruction (הוראות) PDFs from the national planning database.

The mavat site is an Angular SPA with no public REST API docs. Auth tokens are
generated client-side by a browser challenge mechanism, so we automate a real
browser session rather than calling the API directly.

Flow:
    1. Navigate to search page (SV1)
    2. Type plan number, submit → redirects to SV3 with results
    3. Intercept the POST /rest/api/sv3/Search response → extract MP_ID
    4. Navigate directly to plan page: /SV4/1/{MP_ID}/310
    5. Expand "מסמכי התכנית" → "מסמכים מאושרים (מתן תוקף)"
    6. Click the "הורדה כקבצים ב ZIP" next to "הוראות"
    7. Save the downloaded ZIP/PDF

Usage:
    from mavat_client import MavatClient

    client = MavatClient()
    result = client.download_horaot("102-0909267")
    print(result)  # {"status": "success", "file_path": "tmp/mavat_plans/102-0909267.zip", ...}
"""

import logging
import time
import zipfile
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Page

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MAVAT_SEARCH_URL = "https://mavat.iplan.gov.il/SV1"
MAVAT_PLAN_URL_TEMPLATE = "https://mavat.iplan.gov.il/SV4/1/{mp_id}/310"


class MavatClient:
    """Fetches zoning plan documents from mavat.iplan.gov.il.

    Uses Playwright headless browser to navigate the Angular SPA,
    search for plans by number, and download הוראות (instruction) documents.
    """

    def __init__(
        self,
        headless: bool = True,
        output_dir: Path = Path("tmp/mavat_plans"),
    ) -> None:
        """Initialize the mavat client.

        Args:
            headless: Run browser in headless mode (set False for debugging).
            output_dir: Directory to save downloaded documents.
        """
        self.headless = headless
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def search_plan(self, plan_number: str) -> Optional[dict]:
        """Search for a plan by number on mavat.

        Opens the search page, types the plan number, intercepts the search
        API response, and returns the first result.

        Args:
            plan_number: The תב"ע number (e.g., "102-0909267").

        Returns:
            Search result dict with MP_ID, ENTITY_NAME, IS_EXIST_INSTRUCTION_FILE,
            etc., or None if not found.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="he-IL",
            )
            page = context.new_page()
            search_result = self._do_search(page, plan_number)
            browser.close()

        if search_result:
            logger.info(
                "Found plan: %s — %s (MP_ID: %s)",
                plan_number,
                search_result.get("ENTITY_NAME"),
                search_result.get("MP_ID"),
            )
        else:
            logger.warning("No results found for plan: %s", plan_number)

        return search_result

    def download_horaot(self, plan_number: str) -> dict:
        """Full pipeline: search for plan → navigate to it → download הוראות.

        Args:
            plan_number: The תב"ע number (e.g., "102-0909267").

        Returns:
            Result dict with keys:
                status: "success" | "not_found" | "no_instructions" | "download_failed"
                plan_number: The input plan number.
                mp_id: Mavat master plan ID (if found).
                entity_name: Plan name in Hebrew (if found).
                file_path: Path to downloaded file (if success).
                error: Error message (if failed).
        """
        safe_name = plan_number.replace("/", "_").replace("\\", "_")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="he-IL",
                accept_downloads=True,
            )
            page = context.new_page()

            # === STEP 1: Search for the plan ===
            logger.info("Step 1: Searching for plan %s", plan_number)
            search_result = self._do_search(page, plan_number)

            if not search_result:
                logger.warning("Plan not found: %s", plan_number)
                browser.close()
                return {"status": "not_found", "plan_number": plan_number}

            mp_id = int(search_result["MP_ID"])
            entity_name = search_result.get("ENTITY_NAME", "")
            has_instructions = search_result.get(
                "IS_EXIST_INSTRUCTION_FILE", 0
            )

            logger.info(
                "Found: %s — %s (MP_ID: %d, has_instructions: %s)",
                plan_number,
                entity_name,
                mp_id,
                bool(has_instructions),
            )

            if not has_instructions:
                logger.warning(
                    "Plan %s has no instruction file", plan_number
                )
                browser.close()
                return {
                    "status": "no_instructions",
                    "plan_number": plan_number,
                    "mp_id": mp_id,
                    "entity_name": entity_name,
                }

            # === STEP 2: Navigate to plan page ===
            plan_url = MAVAT_PLAN_URL_TEMPLATE.format(mp_id=mp_id)
            logger.info("Step 2: Navigating to plan page: %s", plan_url)
            page.goto(plan_url, wait_until="domcontentloaded", timeout=45000)
            # Wait for Angular to render the plan page content
            page.wait_for_selector("text=מסמכי התכנית", timeout=15000)
            time.sleep(2)

            # === STEP 3: Download הוראות ===
            logger.info("Step 3: Navigating to הוראות download")
            downloaded_path = self._click_through_and_download(
                page, safe_name
            )

            browser.close()

        if downloaded_path:
            # Extract PDF from ZIP if needed
            final_path = self._extract_pdf_if_zip(
                downloaded_path, safe_name
            )
            return {
                "status": "success",
                "plan_number": plan_number,
                "mp_id": mp_id,
                "entity_name": entity_name,
                "file_path": str(final_path),
            }

        return {
            "status": "download_failed",
            "plan_number": plan_number,
            "mp_id": mp_id,
            "entity_name": entity_name,
            "error": "Could not locate or trigger the הוראות download",
        }

    def download_by_mp_id(self, mp_id: str, plan_number: str = "unknown") -> dict:
        """Download הוראות by navigating directly to the plan page via MP_ID.
        
        Args:
            mp_id: The internal Mavat plan ID (e.g. from URL).
            plan_number: Optional plan number for naming the file.
            
        Returns:
            Result dict (same as download_horaot).
        """
        safe_name = plan_number.replace("/", "_").replace("\\", "_")
        if plan_number == "unknown":
            safe_name = f"mp_{mp_id}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="he-IL",
                accept_downloads=True,
            )
            page = context.new_page()

            # Navigate directly
            plan_url = MAVAT_PLAN_URL_TEMPLATE.format(mp_id=mp_id)
            logger.info("Direct navigation to plan page: %s", plan_url)
            page.goto(plan_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_selector("text=מסמכי התכנית", timeout=15000)
            time.sleep(2)

            # Try to scrape the real plan number from the page if unknown
            entity_name = ""
            if plan_number == "unknown":
                try:
                    # Generic heuristic to find title/plan number
                    title_elem = page.locator(".page-title, h1").first
                    if title_elem.is_visible():
                        entity_name = title_elem.inner_text()
                        # Extract something that looks like a plan number
                        # (This is a best-effort, might need regex refinement)
                        pass
                except:
                    pass

            # Download logic
            downloaded_path = self._click_through_and_download(page, safe_name)
            
            browser.close()
            
        if downloaded_path:
            final_path = self._extract_pdf_if_zip(downloaded_path, safe_name)
            return {
                "status": "success",
                "plan_number": plan_number,
                "mp_id": mp_id,
                "entity_name": entity_name,
                "file_path": str(final_path),
            }
            
        return {
            "status": "download_failed",
            "plan_number": plan_number,
            "mp_id": mp_id,
            "error": f"Could not download from direct MP_ID {mp_id}",
        }

    def _do_search(self, page: Page, plan_number: str) -> Optional[dict]:
        """Navigate to search page, type plan number, submit, and return result.

        Uses page.expect_response() to synchronously wait for the search API
        response, avoiding race conditions with browser close.

        Args:
            page: Playwright page instance.
            plan_number: The plan number to search for.

        Returns:
            First search result dict, or None if not found.
        """
        page.goto(MAVAT_SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        # Wait for Angular to render — look for the search button "חיפוש"
        # which appears next to the search input
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        # Find the search input: it's a visible text input (not checkbox)
        # with a placeholder attribute. Use role-based or type-based selector.
        search_input = page.locator(
            "input[type='text'][placeholder], "
            "input[type='search'][placeholder]"
        ).first
        try:
            search_input.wait_for(state="visible", timeout=10000)
        except Exception:
            # Fallback: try any visible input that's not a checkbox
            logger.info("Primary selector failed, trying fallback")
            all_inputs = page.locator("input:visible")
            for i in range(all_inputs.count()):
                inp = all_inputs.nth(i)
                inp_type = inp.get_attribute("type") or "text"
                if inp_type not in ("checkbox", "hidden", "radio"):
                    search_input = inp
                    break
            else:
                logger.error("Could not find search input")
                return None

        search_input.fill(plan_number)
        time.sleep(0.5)

        # Submit search and wait for the API response synchronously
        with page.expect_response(
            lambda r: "/rest/api/sv3/Search" in r.url and r.status == 200,
            timeout=15000,
        ) as response_info:
            search_input.press("Enter")

        response = response_info.value
        try:
            data = response.json()
            for item in data:
                if item.get("type") == "1":
                    dt_results = item["result"].get("dtResults", [])
                    if dt_results:
                        return dt_results[0]
        except Exception as e:
            logger.warning("Failed to parse search response: %s", e)

        return None

    def _click_through_and_download(
        self, page: Page, safe_name: str
    ) -> Optional[Path]:
        """Click through document sections and download the הוראות PDF.

        The exact UI flow (4 clicks):
            1. Click "מסמכי התכנית" (green notebook icon) to expand
            2. Click "מסמכים מאושרים (מתן תוקף)" or "מסמכים בתהליך" to expand
            3. Click "הוראות" sub-dropdown to expand
            4. Click the PDF icon on the "תדפיס הוראות התכנית" row

        Args:
            page: Playwright page instance on the plan page.
            safe_name: Filesystem-safe plan name for saving files.

        Returns:
            Path to downloaded file, or None if download failed.
        """
        try:
            # Step 1: Click "מסמכי התכנית" to expand
            docs_header = page.locator("text=מסמכי התכנית").first
            if docs_header.is_visible(timeout=5000):
                docs_header.click()
                time.sleep(2)
                logger.info("Expanded 'מסמכי התכנית'")
            else:
                logger.warning("'מסמכי התכנית' not visible")
                page.screenshot(
                    path=str(
                        self.output_dir / f"debug_{safe_name}_step1.png"
                    )
                )
                return None

            # Step 2: Click "מסמכים מאושרים (מתן תוקף)" to expand.
            # Fallback to "מסמכים בתהליך" for plans not yet approved.
            approved_header = page.locator("text=מסמכים מאושרים").first
            if approved_header.is_visible(timeout=5000):
                approved_header.click()
                time.sleep(2)
                logger.info("Expanded 'מסמכים מאושרים (מתן תוקף)'")
            else:
                in_process_header = page.locator("text=מסמכים בתהליך").first
                if in_process_header.is_visible(timeout=3000):
                    in_process_header.click()
                    time.sleep(2)
                    logger.info("Expanded 'מסמכים בתהליך' (fallback)")
                else:
                    logger.warning(
                        "'מסמכים מאושרים' and 'מסמכים בתהליך' both not visible"
                    )
                    page.screenshot(
                        path=str(
                            self.output_dir / f"debug_{safe_name}_step2.png"
                        )
                    )
                    return None

            # Step 3: Click "הוראות" sub-dropdown to expand.
            # Must use exact match — "text=הוראות" also matches
            # "עיקר הוראותיה" higher on the page.
            horaot_header = page.get_by_text("הוראות", exact=True).first
            # Scroll to it first since it may be below the fold
            horaot_header.scroll_into_view_if_needed()
            if horaot_header.is_visible(timeout=5000):
                horaot_header.click()
                time.sleep(2)
                logger.info("Expanded 'הוראות'")
            else:
                logger.warning("'הוראות' (exact) not visible")
                page.screenshot(
                    path=str(
                        self.output_dir / f"debug_{safe_name}_step3.png"
                    )
                )
                return None

            # Take debug screenshot showing the expanded הוראות section
            page.screenshot(
                path=str(
                    self.output_dir / f"debug_{safe_name}_horaot_expanded.png"
                )
            )

            # Step 4: Find and click the PDF download icon on the
            # "תדפיס הוראות התכנית" row.
            # The row has two PDF icons: one with eye (preview) and one
            # for download. We want the download one (usually second).
            return self._click_pdf_download(page, safe_name)

        except Exception as e:
            logger.error("Error navigating document sections: %s", e)
            page.screenshot(
                path=str(self.output_dir / f"debug_{safe_name}_error.png")
            )
            return None

    def _click_pdf_download(
        self, page: Page, safe_name: str
    ) -> Optional[Path]:
        """Find and click the PDF download icon in the הוראות section.

        After expanding הוראות, the page shows a row for "תדפיס הוראות התכנית"
        with two PDF icon images:
            - img.sv4-icon-file (preview, src=sv4-icon-pdf-view.svg)
            - img.pdf-download  (download, src=sv4-icon-pdf-download.svg)

        We click the download icon (class "pdf-download").

        Args:
            page: Playwright page with הוראות section expanded.
            safe_name: Filesystem-safe name for saving the file.

        Returns:
            Path to downloaded file, or None.
        """
        # Primary: click the img with class "pdf-download"
        try:
            download_icon = page.locator("img.pdf-download").first
            if download_icon.is_visible(timeout=5000):
                download_icon.scroll_into_view_if_needed()
                logger.info("Found PDF download icon (img.pdf-download)")
                return self._trigger_download(
                    page, download_icon, safe_name
                )
        except Exception as e:
            logger.info("img.pdf-download not found: %s", e)

        # Fallback: any img with src containing "pdf-download"
        try:
            download_icon = page.locator(
                "img[src*='pdf-download']"
            ).first
            if download_icon.is_visible(timeout=3000):
                logger.info("Found PDF download icon by src attribute")
                return self._trigger_download(
                    page, download_icon, safe_name
                )
        except Exception as e:
            logger.info("img[src*='pdf-download'] not found: %s", e)

        logger.warning("No PDF download icon found in הוראות section")
        page.screenshot(
            path=str(self.output_dir / f"debug_{safe_name}_no_pdf.png")
        )
        return None

    def _trigger_download(
        self, page: Page, element: "Locator", safe_name: str
    ) -> Optional[Path]:
        """Click an element and capture the resulting download.

        Args:
            page: Playwright page instance.
            element: The clickable element to trigger download.
            safe_name: Filesystem-safe name for saving.

        Returns:
            Path to saved file, or None if no download was triggered.
        """
        try:
            with page.expect_download(timeout=30000) as download_info:
                element.click()

            download = download_info.value
            suggested = download.suggested_filename
            ext = Path(suggested).suffix if suggested else ".zip"
            save_path = self.output_dir / f"{safe_name}{ext}"
            download.save_as(str(save_path))
            logger.info("Downloaded: %s (%s)", save_path, suggested)
            return save_path
        except Exception as e:
            logger.warning("Download failed after click: %s", e)
            return None

    def _extract_pdf_if_zip(self, file_path: Path, safe_name: str) -> Path:
        """If the downloaded file is a ZIP, extract the PDF from it.

        Args:
            file_path: Path to the downloaded file.
            safe_name: Base name for extracted files.

        Returns:
            Path to the PDF file (either extracted or the original if not ZIP).
        """
        if not file_path.suffix.lower() == ".zip":
            return file_path

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                pdf_files = [
                    n for n in zf.namelist() if n.lower().endswith(".pdf")
                ]
                if pdf_files:
                    # Extract the first PDF
                    pdf_name = pdf_files[0]
                    extracted_path = self.output_dir / f"{safe_name}.pdf"
                    with zf.open(pdf_name) as src, open(
                        extracted_path, "wb"
                    ) as dst:
                        dst.write(src.read())
                    logger.info(
                        "Extracted PDF from ZIP: %s → %s",
                        pdf_name,
                        extracted_path,
                    )
                    return extracted_path
                else:
                    logger.warning("ZIP contains no PDF files: %s", file_path)
                    return file_path
        except zipfile.BadZipFile:
            # Not actually a ZIP — might be a direct PDF with wrong extension
            logger.info("File is not a valid ZIP, treating as PDF")
            pdf_path = file_path.with_suffix(".pdf")
            file_path.rename(pdf_path)
            return pdf_path
