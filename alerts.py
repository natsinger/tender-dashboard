"""
Tender alert engine.

Two alert types:
1. **Watchlist document alerts** — new documents on any team-watched tender.
   All watchlist entries are merged team-wide (regardless of who added them)
   and a single email is sent to ALERT_RECIPIENTS.
2. **New tender alerts** — newly-listed tenders matching criteria
   (CARD_TENDER_TYPES + RELEVANT_PURPOSES).

Sends email notifications via SMTP2GO. Designed to run standalone
in GitHub Actions cron or be imported by other modules.

Usage:
    python alerts.py              # Check all watchlists and send alerts
    python alerts.py --dry-run    # Show what would be sent without sending
"""

import html as _html
import logging
import smtplib
import sys
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

# Add project root to path (for standalone execution)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    ALERT_RECIPIENTS,
    CARD_TENDER_TYPES,
    DASHBOARD_URL,
    RELEVANT_PURPOSES,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    TEAM_EMAIL,
)
from data_client import build_document_url
from db import TenderDB
from user_db import UserDB

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TenderAlert:
    """New documents found for a single watched tender."""

    tender_id: int
    tender_name: str
    city: str
    deadline: str
    new_docs: list[dict] = field(default_factory=list)


@dataclass
class AlertBundle:
    """All document alerts for the team, ready to send as one email."""

    tender_alerts: list[TenderAlert] = field(default_factory=list)

    @property
    def total_docs(self) -> int:
        """Total number of new documents across all tenders."""
        return sum(len(ta.new_docs) for ta in self.tender_alerts)


# ── Alert engine ─────────────────────────────────────────────────────────────

class AlertEngine:
    """Core alert logic: detect new documents/tenders, compose emails, send via SMTP."""

    def __init__(self, db: TenderDB, user_db: UserDB, dry_run: bool = False) -> None:
        """Initialize the alert engine.

        Args:
            db: TenderDB instance for tender/document queries.
            user_db: UserDB instance for watchlist/alert_history (Supabase).
            dry_run: If True, log what would be sent without actually sending.
        """
        self.db = db
        self.user_db = user_db
        self.dry_run = dry_run

    def _verify_smtp_connection(self) -> bool:
        """Quick SMTP EHLO test to verify credentials before processing.

        Returns:
            True if SMTP connection and login succeed, False otherwise.
        """
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.error(
                "SMTP credentials not configured (SMTP_USER or SMTP_PASSWORD empty). "
                "Alert emails cannot be sent."
            )
            return False

        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
            logger.info("SMTP connectivity check passed (%s:%d)", SMTP_HOST, SMTP_PORT)
            return True
        except Exception as exc:
            logger.error(
                "SMTP connectivity check FAILED (%s:%d): %s",
                SMTP_HOST, SMTP_PORT, exc,
            )
            return False

    # ── Watchlist document alerts (team-wide) ─────────────────────────

    def check_and_send(self) -> int:
        """Check all watchlists for new documents and send one team email.

        All watchlist entries across all users are merged. Deduplication
        uses TEAM_EMAIL so the whole team shares a single alert history.

        Returns:
            Number of emails sent (0 or 1, or would-be-sent in dry-run).
        """
        if not self.dry_run:
            if not self._verify_smtp_connection():
                logger.error(
                    "Aborting alert check — SMTP is not reachable. "
                    "Fix SMTP_HOST/SMTP_USER/SMTP_PASSWORD and retry."
                )
                return 0

        watchlist_entries = self.user_db.get_all_active_watchlists()
        if not watchlist_entries:
            logger.info("No active watchlist entries found")
            return 0

        # Merge all entries team-wide: deduplicate by tender_id,
        # keep the earliest created_at per tender for the "since" date.
        tender_since: dict[int, str] = {}
        for entry in watchlist_entries:
            tid = entry["tender_id"]
            created = entry["created_at"]
            if tid not in tender_since or created < tender_since[tid]:
                tender_since[tid] = created

        logger.info(
            "Processing watchlists: %d unique tenders from %d entries",
            len(tender_since), len(watchlist_entries),
        )

        bundle = self._build_team_bundle(tender_since)
        if not bundle or not bundle.tender_alerts:
            logger.info("No new documents found for watched tenders")
            return 0

        logger.info(
            "Team alert: %d tenders with %d new documents",
            len(bundle.tender_alerts), bundle.total_docs,
        )

        if self.dry_run:
            self._log_dry_run(bundle)
            return 1

        success = self._send_watchlist_email(bundle)
        if success:
            self._record_sent_alerts(bundle)
            return 1
        return 0

    def _build_team_bundle(
        self, tender_since: dict[int, str],
    ) -> Optional[AlertBundle]:
        """Build an alert bundle for the team by checking each watched tender.

        Uses TEAM_EMAIL for deduplication in alert_history so the whole
        team shares a single set of "already sent" document IDs.

        Args:
            tender_since: Mapping of tender_id → earliest watchlist created_at.

        Returns:
            AlertBundle with non-empty tender alerts, or None.
        """
        bundle = AlertBundle()

        for tender_id, since_date in tender_since.items():
            # Dedup against TEAM_EMAIL (shared team history)
            sent_ids = self.user_db.get_sent_doc_ids(TEAM_EMAIL, tender_id)
            new_docs = self.db.get_new_docs_excluding(tender_id, since_date, sent_ids)

            if not new_docs:
                continue

            tender = self.db.get_tender_by_id(tender_id)
            if not tender:
                continue

            alert = TenderAlert(
                tender_id=tender_id,
                tender_name=tender.get("tender_name", ""),
                city=tender.get("city", ""),
                deadline=tender.get("deadline", ""),
                new_docs=new_docs,
            )
            bundle.tender_alerts.append(alert)

        return bundle if bundle.tender_alerts else None

    def _record_sent_alerts(self, bundle: AlertBundle) -> None:
        """Record all sent alerts in Supabase alert_history for deduplication.

        Uses TEAM_EMAIL so all team members share a single dedup set.
        """
        for ta in bundle.tender_alerts:
            for doc in ta.new_docs:
                self.user_db.record_alert_sent(
                    TEAM_EMAIL, ta.tender_id, doc["row_id"],
                )

    def _log_dry_run(self, bundle: AlertBundle) -> None:
        """Log what would be sent in dry-run mode."""
        logger.info("[DRY RUN] Would send email to: %s", ALERT_RECIPIENTS)
        for ta in bundle.tender_alerts:
            logger.info(
                "  Tender %d (%s): %d new docs",
                ta.tender_id, ta.tender_name, len(ta.new_docs),
            )
            for doc in ta.new_docs:
                doc_label = doc.get("description") or doc.get("doc_name", "מסמך")
                logger.info("    - %s (%s)", doc_label, doc["first_seen"])

    # ── Watchlist email composition ───────────────────────────────────

    def _send_watchlist_email(self, bundle: AlertBundle) -> bool:
        """Compose and send watchlist document alert to the team.

        Args:
            bundle: All alerts to include in the email.

        Returns:
            True if sent successfully.
        """
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured, skipping email")
            return False

        subject = f"🏗️ עדכון מכרזים — {bundle.total_docs} מסמכים חדשים"
        html_body = self._compose_watchlist_html(bundle)

        return send_smtp_email(to=ALERT_RECIPIENTS, subject=subject, html_body=html_body)

    def _compose_watchlist_html(self, bundle: AlertBundle) -> str:
        """Build Hebrew RTL HTML email with document links.

        Args:
            bundle: All document alerts.

        Returns:
            HTML string for the email body.
        """
        from datetime import date as _date

        today_str = _date.today().strftime("%d/%m/%Y")

        tender_blocks = []
        for ta in bundle.tender_alerts:
            doc_items = []
            for doc in ta.new_docs:
                doc_url_data = {
                    "MichrazID": ta.tender_id,
                    "RowID": doc["row_id"],
                    "Size": doc.get("size", 0),
                    "PirsumType": doc.get("pirsum_type", 0),
                    "DocName": doc.get("doc_name", "document.pdf"),
                    "Teur": doc.get("description", ""),
                    "FileType": doc.get("file_type", "application/pdf"),
                }
                doc_url = build_document_url(doc_url_data)
                doc_desc = _html.escape(
                    doc.get("description", "") or doc.get("doc_name", "מסמך")
                )
                doc_date = _html.escape(doc.get("first_seen", ""))
                safe_url = _html.escape(doc_url, quote=True)

                doc_items.append(
                    f'<li style="margin-bottom:8px;">'
                    f'<span style="font-weight:500;color:#2B3674;">{doc_desc}</span>'
                    f'<span style="color:#A3AED0;font-size:13px;"> ({doc_date})</span>'
                    f'<br>'
                    f'<a href="{safe_url}" style="color:#4318FF;text-decoration:none;'
                    f'font-size:13px;">⬇ הורד מסמך</a>'
                    f'</li>'
                )

            deadline_str = _html.escape(ta.deadline or "לא צוין")
            docs_html = "\n".join(doc_items)

            tender_blocks.append(f"""
            <div style="margin:16px 0;padding:12px;background:#f8f9fc;
                        border-radius:8px;border-right:4px solid #4318FF;">
              <h3 style="color:#2B3674;margin:0 0 8px 0;">
                מכרז {ta.tender_id} — {_html.escape(ta.tender_name)}
              </h3>
              <p style="color:#A3AED0;margin:0 0 8px 0;">
                {_html.escape(ta.city)} | מועד סגירה: {deadline_str}
              </p>
              <p style="font-weight:600;color:#2B3674;">מסמכים חדשים:</p>
              <ul style="padding-right:20px;">{docs_html}</ul>
            </div>""")

        tenders_html = "\n".join(tender_blocks)

        dashboard_button = ""
        if DASHBOARD_URL:
            dashboard_button = f"""
            <p style="text-align:center;">
              <a href="{DASHBOARD_URL}"
                 style="display:inline-block;background:#4318FF;color:#fff;
                        padding:10px 24px;border-radius:20px;text-decoration:none;
                        font-weight:500;">
                פתח לוח מכרזים
              </a>
            </p>"""

        return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;direction:rtl;text-align:right;
             background:#f4f7fe;padding:20px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;
              padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <h2 style="color:#2B3674;margin-bottom:4px;">
      עדכון מכרזים — מסמכים חדשים
    </h2>
    <p style="color:#A3AED0;font-size:14px;">{today_str}</p>

    <hr style="border:1px solid #E9EDF7;">
    {tenders_html}
    <hr style="border:1px solid #E9EDF7;">
    {dashboard_button}

    <p style="color:#A3AED0;font-size:12px;text-align:center;margin-top:16px;">
      התראה זו נשלחה אוטומטית ממערכת מעקב מכרזי קרקע.<br>
      לביטול התראות, הסר/י מכרזים מרשימת המעקב בלוח.
    </p>
  </div>
</body>
</html>"""

    # ── New tender alerts ─────────────────────────────────────────────

    def send_new_tender_alert(self, new_tenders: list[dict]) -> bool:
        """Send an alert email for newly-listed tenders matching criteria.

        Filters new tenders by CARD_TENDER_TYPES and RELEVANT_PURPOSES,
        then sends a single email to ALERT_RECIPIENTS.

        Args:
            new_tenders: List of tender dicts (from the API fetch DataFrame).
                Each dict must have: tender_id, tender_name, city, deadline,
                tender_type_code, tender_type, purpose, units.

        Returns:
            True if email was sent (or would be in dry-run), False if
            no matching tenders or send failed.
        """
        # Filter to matching criteria
        matching = [
            t for t in new_tenders
            if (
                t.get("tender_type_code") in CARD_TENDER_TYPES
                and (
                    not t.get("purpose")
                    or t.get("purpose") in RELEVANT_PURPOSES
                )
            )
        ]

        if not matching:
            logger.info("No new tenders match alert criteria")
            return False

        logger.info(
            "New tender alert: %d tenders match criteria (from %d new)",
            len(matching), len(new_tenders),
        )

        if self.dry_run:
            logger.info("[DRY RUN] Would send new-tender alert to: %s", ALERT_RECIPIENTS)
            for t in matching:
                logger.info(
                    "  Tender %d: %s (%s) — %s",
                    t.get("tender_id", 0),
                    t.get("tender_name", ""),
                    t.get("city", ""),
                    t.get("tender_type", ""),
                )
            return True

        subject = f"🆕 {len(matching)} מכרזים חדשים פורסמו"
        html_body = self._compose_new_tender_html(matching)

        return send_smtp_email(to=ALERT_RECIPIENTS, subject=subject, html_body=html_body)

    def _compose_new_tender_html(self, tenders: list[dict]) -> str:
        """Build Hebrew RTL HTML email listing newly-listed tenders.

        Args:
            tenders: List of tender dicts matching alert criteria.

        Returns:
            HTML string for the email body.
        """
        from datetime import date as _date

        today_str = _date.today().strftime("%d/%m/%Y")

        tender_blocks = []
        for t in tenders:
            tid = t.get("tender_id", 0)
            name = _html.escape(str(t.get("tender_name", "")))
            city = _html.escape(str(t.get("city", "—")))
            ttype = _html.escape(str(t.get("tender_type", "—")))
            purpose = _html.escape(str(t.get("purpose", "—")))
            units = t.get("units")
            units_str = str(units) if units else "—"
            deadline = _html.escape(str(t.get("deadline", "לא צוין")))

            tender_blocks.append(f"""
            <div style="margin:16px 0;padding:12px;background:#f8f9fc;
                        border-radius:8px;border-right:4px solid #22C55E;">
              <h3 style="color:#2B3674;margin:0 0 8px 0;">
                מכרז {tid} — {name}
              </h3>
              <p style="color:#A3AED0;margin:0 0 4px 0;">
                {city} | {ttype} | {purpose}
              </p>
              <p style="color:#A3AED0;margin:0 0 4px 0;">
                יח"ד: {units_str} | מועד סגירה: {deadline}
              </p>
            </div>""")

        tenders_html = "\n".join(tender_blocks)

        dashboard_button = ""
        if DASHBOARD_URL:
            dashboard_button = f"""
            <p style="text-align:center;">
              <a href="{DASHBOARD_URL}"
                 style="display:inline-block;background:#22C55E;color:#fff;
                        padding:10px 24px;border-radius:20px;text-decoration:none;
                        font-weight:500;">
                צפה בלוח מכרזים
              </a>
            </p>"""

        return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;direction:rtl;text-align:right;
             background:#f4f7fe;padding:20px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;
              padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <h2 style="color:#2B3674;margin-bottom:4px;">
      🆕 מכרזים חדשים פורסמו
    </h2>
    <p style="color:#A3AED0;font-size:14px;">{today_str} | {len(tenders)} מכרזים חדשים</p>

    <hr style="border:1px solid #E9EDF7;">
    {tenders_html}
    <hr style="border:1px solid #E9EDF7;">
    {dashboard_button}

    <p style="color:#A3AED0;font-size:12px;text-align:center;margin-top:16px;">
      התראה זו נשלחה אוטומטית ממערכת מעקב מכרזי קרקע.<br>
      מכרזים מסוג: פומבי רגיל, מחיר מטרה, דיור במחיר מופחת.
    </p>
  </div>
</body>
</html>"""


# ── SMTP sending ─────────────────────────────────────────────────────────────

def send_smtp_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    smtp_host: str = SMTP_HOST,
    smtp_port: int = SMTP_PORT,
    smtp_user: str = SMTP_USER,
    smtp_password: str = SMTP_PASSWORD,
    from_addr: str = SMTP_FROM,
) -> bool:
    """Send an HTML email via SMTP with TLS.

    Args:
        to: Recipient email address or list of addresses.
        subject: Email subject line.
        html_body: HTML content for the email body.
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port (587 for TLS).
        smtp_user: SMTP username.
        smtp_password: SMTP password.
        from_addr: Sender email address.

    Returns:
        True if sent successfully, False otherwise.
    """
    recipients = to if isinstance(to, list) else [to]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr or smtp_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(msg["From"], recipients, msg.as_string())
        logger.info("Email sent to %s", ", ".join(recipients))
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", ", ".join(recipients), exc)
        return False


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point for running alerts standalone."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )

    dry_run = "--dry-run" in sys.argv

    if dry_run:
        logger.info("Running in DRY RUN mode (no emails will be sent)")

    db = TenderDB()
    user_db = UserDB()
    engine = AlertEngine(db, user_db, dry_run=dry_run)
    sent = engine.check_and_send()

    logger.info("Done. %d email(s) %s.", sent, "would be sent" if dry_run else "sent")


if __name__ == "__main__":
    main()
