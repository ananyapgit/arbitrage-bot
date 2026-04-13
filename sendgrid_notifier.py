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
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except OSError as e:
        logging.error("broadcast_log write failed: %s", e)


class SendGridNotifier:
    """Broadcasts HTML loot alerts to subscribers when SendGrid is configured."""

    def __init__(self) -> None:
        self.api_key = (os.getenv("SENDGRID_API_KEY") or "").strip()
        self.from_email = (os.getenv("SENDGRID_FROM_EMAIL") or "deals@noreply.local").strip()

    def load_subscribers(self) -> list[str]:
        if not SUBSCRIBERS_FILE.is_file():
            print(f"[CRITICAL] No subscribers found in data folder: missing {SUBSCRIBERS_FILE}", flush=True)
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
        if not out:
            print(f"[CRITICAL] No subscribers found in data folder: empty {SUBSCRIBERS_FILE}", flush=True)
        return out

    def broadcast_loot_deal(self, deal: dict, discount_pct: float) -> int:
        """
        Sends one HTML email per subscriber. Returns number of successful sends.
        """
        print("!!! EMAIL ENGINE ACTIVATED !!!", flush=True)
        if not self.api_key:
            logging.info("SendGrid: SENDGRID_API_KEY not set; skipping loot broadcast.")
            return 0

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
        except ImportError:
            logging.error("SendGrid: install the 'sendgrid' package (pip install sendgrid).")
            return 0

        # STRICT SENDER CHECK: Ensure from_email matches environment variable
        expected_from_email = os.getenv('SENDGRID_FROM_EMAIL')
        if expected_from_email and self.from_email != expected_from_email.strip():
            logging.error(f"SendGrid: from_email mismatch. Expected: {expected_from_email}, Got: {self.from_email}")
            return 0
        
        # FORCE USE OF ENVIRONMENT SENDER EMAIL
        if expected_from_email:
            self.from_email = expected_from_email.strip()

        # LOWER THRESHOLD FOR TESTING: Allow deals >10% if TEST_MODE=True
        test_mode = os.getenv('TEST_MODE', 'false').lower() in {'true', '1', 'yes'}
        force_email_test = os.getenv('FORCE_EMAIL_TEST', 'false').lower() in {'true', '1', 'yes'}
        threshold = 10.0 if (test_mode or force_email_test) else 20.0
        
        if discount_pct < threshold:
            logging.info(f"SendGrid: discount {discount_pct}% below threshold {threshold}%; skipping broadcast.")
            return 0

        recipients = self.load_subscribers()
        if not recipients:
            logging.info("SendGrid: no subscribers in %s", SUBSCRIBERS_FILE)
            return 0

        # LOGGING FOR GITHUB ACTIONS
        deal_id = str(deal.get("id") or deal.get("deal_id") or "unknown")
        print(f"[EMAIL] Attempting to send deal {deal_id} to {len(recipients)} recipients", flush=True)

        title = html.escape(str(deal.get("title") or "Deal").strip())
        link = str(deal.get("affiliate_url") or deal.get("url") or "").strip()
        link_esc = html.escape(link, quote=True)
        deal_id = str(deal.get("id") or deal.get("deal_id") or link[-24:] or "unknown")

        if not link:
            logging.warning("SendGrid: missing affiliate/url for deal_id=%s; skipping.", deal_id)
            return 0

        html_body = f"""<!DOCTYPE html>
<html><body style="margin:0;background:#000000;font-family:Inter,system-ui,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:24px 12px;">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#1A1A1A;border:2px solid #FFD700;border-radius:12px;padding:32px 28px;">
        <tr><td style="font-size:12px;letter-spacing:0.15em;color:#FFD700;text-transform:uppercase;font-weight:600;">LOOT ALERT</td></tr>
        <tr><td style="padding-top:12px;font-size:22px;font-weight:800;color:#FFFFFF;line-height:1.3;">{title}</td></tr>
        <tr><td style="padding-top:16px;font-size:16px;color:#FFD700;font-weight:600;">{discount_pct:.0f}%+ DISCOUNT DETECTED</td></tr>
        <tr><td style="padding-top:8px;font-size:14px;color:#CCCCCC;">High-value arbitrage deal from live scanner.</td></tr>
        <tr><td style="padding-top:28px;" align="center">
          <a href="{link_esc}" style="display:inline-block;padding:16px 36px;background:#FFD700;color:#000000;font-weight:900;
            text-decoration:none;border-radius:8px;font-size:16px;letter-spacing:0.02em;text-transform:uppercase;">BUY NOW</a>
        </td></tr>
        <tr><td style="padding-top:24px;font-size:11px;color:#666666;">Automated message - do not reply.</td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

        if not html_body or "<html" not in html_body.lower():
            logging.error("SendGrid: empty/invalid HTML body; aborting broadcast.")
            return 0

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
        if sent == len(recipients):
            print(f"[EMAIL:SUCCESS] Sent to {sent} subscribers", flush=True)
        else:
            print(f"[EMAIL:PARTIAL] Sent to {sent}/{len(recipients)} subscribers", flush=True)
        return sent

    def broadcast_daily_loot(self, deals: list[dict], subject: str = "Daily Loot") -> int:
        """
        Consolidated HTML email (one send per subscriber).
        Returns number of successful sends.
        """
        print("!!! EMAIL ENGINE ACTIVATED !!!", flush=True)
        if not self.api_key:
            logging.info("SendGrid: SENDGRID_API_KEY not set; skipping daily loot broadcast.")
            return 0
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
        except ImportError:
            logging.error("SendGrid: install the 'sendgrid' package (pip install sendgrid).")
            return 0

        expected_from_email = os.getenv("SENDGRID_FROM_EMAIL")
        if expected_from_email and self.from_email != expected_from_email.strip():
            logging.error("SendGrid: from_email mismatch. Expected: %s, Got: %s", expected_from_email, self.from_email)
            return 0
        if expected_from_email:
            self.from_email = expected_from_email.strip()

        recipients = self.load_subscribers()
        if not recipients:
            logging.info("SendGrid: no subscribers in %s", SUBSCRIBERS_FILE)
            return 0

        top = []
        for d in deals[:12]:
            title = html.escape(str(d.get("title") or "Deal"))
            link = str(d.get("affiliate_url") or d.get("url") or "").strip()
            if not link:
                continue
            top.append((title, html.escape(link, quote=True)))

        if not top:
            print("[CRITICAL] Daily Loot email body empty (no valid links)", flush=True)
            return 0

        items = "".join(
            [f"<tr><td style='padding:10px 0;border-bottom:1px solid #2A2A2A;'><a href='{u}' style='color:#FFD700;text-decoration:none;font-weight:700;'>{t}</a></td></tr>" for t, u in top]
        )
        html_body = f"""<!DOCTYPE html>
<html><body style="margin:0;background:#000000;font-family:Inter,system-ui,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:24px 12px;">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#1A1A1A;border:2px solid #FFD700;border-radius:12px;padding:28px 24px;">
        <tr><td style="font-size:12px;letter-spacing:0.15em;color:#FFD700;text-transform:uppercase;font-weight:600;">DAILY LOOT</td></tr>
        <tr><td style="padding-top:10px;font-size:16px;color:#FFFFFF;font-weight:800;">Top verified deals</td></tr>
        <tr><td style="padding-top:14px;">
          <table width="100%" cellspacing="0" cellpadding="0">{items}</table>
        </td></tr>
        <tr><td style="padding-top:18px;font-size:11px;color:#666666;">Automated digest - do not reply.</td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

        client = SendGridAPIClient(self.api_key)
        sent = 0
        for to_addr in recipients:
            try:
                msg = Mail(from_email=self.from_email, to_emails=to_addr, subject=subject, html_content=html_body)
                resp = client.send(msg)
                code = getattr(resp, "status_code", None)
                if code and int(code) >= 400:
                    logging.warning("SendGrid error %s for %s", code, to_addr)
                else:
                    sent += 1
            except Exception as e:
                logging.warning("SendGrid send failed for %s: %s", to_addr, e)

        if sent:
            _log_broadcast("daily_loot", sent)
        if sent == len(recipients):
            print(f"[EMAIL:SUCCESS] Sent to {sent} subscribers", flush=True)
        else:
            print(f"[EMAIL:PARTIAL] Sent to {sent}/{len(recipients)} subscribers", flush=True)
        return sent
