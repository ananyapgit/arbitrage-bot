"""
Serverless-style email outreach via SendGrid for high-loot deals.
Reads dashboard/public/data/subscribers.txt (one email per line).
"""

from __future__ import annotations

import csv
import html
import logging
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("dashboard/public/data")
SUBSCRIBERS_FILE = DATA_DIR / "subscribers.txt"
BROADCAST_LOG = DATA_DIR / "broadcast_log.csv"


def _log_broadcast(deal_id: str, recipients: int) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    exists = BROADCAST_LOG.is_file()
    try:
        with open(BROADCAST_LOG, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["timestamp", "deal_id", "recipients"])
            w.writerow([datetime.now().isoformat(), deal_id, recipients])
    except OSError as e:
        logging.error("broadcast_log write failed: %s", e)


class SendGridNotifier:
    """Broadcasts HTML loot alerts to subscribers when SendGrid is configured."""

    def __init__(self) -> None:
        self.api_key = (os.getenv("SENDGRID_API_KEY") or "").strip()
        self.from_email = (os.getenv("SENDGRID_FROM_EMAIL") or "deals@noreply.local").strip()

    def load_subscribers(self) -> list[str]:
        if not SUBSCRIBERS_FILE.is_file():
            return []
        seen: set[str] = set()
        out: list[str] = []
        for line in SUBSCRIBERS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "@" not in line:
                continue
            if line.lower() in seen:
                continue
            seen.add(line.lower())
            out.append(line)
        return out

    def broadcast_loot_deal(self, deal: dict, discount_pct: float) -> int:
        """
        Sends one HTML email per subscriber. Returns number of successful sends.
        """
        if not self.api_key:
            logging.info("SendGrid: SENDGRID_API_KEY not set; skipping loot broadcast.")
            return 0

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
        except ImportError:
            logging.error("SendGrid: install the 'sendgrid' package (pip install sendgrid).")
            return 0

        recipients = self.load_subscribers()
        if not recipients:
            logging.info("SendGrid: no subscribers in %s", SUBSCRIBERS_FILE)
            return 0

        title = html.escape(str(deal.get("title") or "Deal").strip())
        link = str(deal.get("affiliate_url") or deal.get("url") or "").strip()
        link_esc = html.escape(link, quote=True)
        deal_id = str(deal.get("id") or deal.get("deal_id") or link[-24:] or "unknown")

        html_body = f"""<!DOCTYPE html>
<html><body style="margin:0;background:#F2F0EB;font-family:Inter,system-ui,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:24px 12px;">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#FFFFFF;border:1px solid #E3E3E0;border-radius:16px;padding:28px 24px;">
        <tr><td style="font-size:11px;letter-spacing:0.14em;color:#6B6B6B;text-transform:uppercase;">Loot alert</td></tr>
        <tr><td style="padding-top:8px;font-size:20px;font-weight:700;color:#1A1A1A;line-height:1.25;">{title}</td></tr>
        <tr><td style="padding-top:12px;font-size:15px;color:#333;">{discount_pct:.0f}%+ discount detected on the arbitrage bot.</td></tr>
        <tr><td style="padding-top:24px;" align="center">
          <a href="{link_esc}" style="display:inline-block;padding:14px 32px;background:#FFD700;color:#000000;font-weight:800;
            text-decoration:none;border-radius:10px;font-size:15px;letter-spacing:0.02em;">Buy now</a>
        </td></tr>
        <tr><td style="padding-top:20px;font-size:11px;color:#9A9A97;">Automated message — do not reply.</td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

        client = SendGridAPIClient(self.api_key)
        sent = 0
        for to_addr in recipients:
            try:
                message = Mail(
                    from_email=self.from_email,
                    to_emails=to_addr,
                    subject=f"Loot: {title[:60]}",
                    html_content=html_body,
                )
                resp = client.send(message)
                code = getattr(resp, "status_code", None)
                if code and int(code) >= 400:
                    logging.warning("SendGrid error %s for %s", code, to_addr)
                else:
                    sent += 1
            except Exception as e:
                logging.warning("SendGrid send failed for %s: %s", to_addr, e)

        if sent:
            _log_broadcast(deal_id, sent)
        return sent
