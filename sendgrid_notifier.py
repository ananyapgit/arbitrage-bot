"""
Email outreach via native SMTP (replacing SendGrid).
Reads dashboard-new/public/data/subscribers.txt (one email per line).
"""

from __future__ import annotations

import csv
import html
import logging
import os
import smtplib
import ssl
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DATA_DIR = Path("dashboard-new/public/data")
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


class SMTPNotifier:
    """Broadcasts HTML loot alerts to subscribers using native SMTP."""

    def __init__(self) -> None:
        self.host = (os.getenv("EMAIL_HOST") or "smtp.gmail.com").strip()
        self.port = int(os.getenv("EMAIL_PORT") or "587")
        self.user = (os.getenv("EMAIL_USER") or "").strip()
        self.password = (os.getenv("EMAIL_PASS") or "").strip()
        
        if self.user:
            print(f"[DEBUG] SMTP User loaded: {self.user}", flush=True)
        self.from_email = self.user

    def load_subscribers(self) -> list[str]:
        potential_paths = [
            SUBSCRIBERS_FILE,
            Path("dashboard-new/public/data/subscribers.txt"),
            Path(__file__).parent / "dashboard-new/public/data/subscribers.txt"
        ]
        
        actual_file = None
        for p in potential_paths:
            if p.is_file():
                actual_file = p
                break
        
        if not actual_file:
            print(f"[CRITICAL] No subscribers found in data folder: missing {SUBSCRIBERS_FILE}", flush=True)
            return []
            
        print(f"[DEBUG] Loading subscribers from: {actual_file.absolute()}", flush=True)
        seen: set[str] = set()
        out: list[str] = []
        try:
            content = actual_file.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            print(f"[DEBUG] Found {len(lines)} raw lines in subscribers file", flush=True)
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "@" not in line:
                    continue
                if line.lower() in seen:
                    continue
                seen.add(line.lower())
                out.append(line)
        except Exception as e:
            print(f"[CRITICAL] Failed to read subscribers file: {e}", flush=True)
            
        if not out:
            print(f"[CRITICAL] No valid subscribers parsed from {actual_file}", flush=True)
        else:
            print(f"[DEBUG] Successfully loaded {len(out)} unique subscribers", flush=True)
        return out

    def broadcast_loot_deal(self, deal: dict, discount_pct: float) -> int:
        """
        Sends one HTML email per subscriber. Returns number of successful sends.
        """
        print("!!! EMAIL ENGINE ACTIVATED !!!", flush=True)
        if not self.from_email:
            raise ValueError("EMAIL_USER is missing")
        if not self.password:
            logging.info("SMTP: EMAIL_PASS not set; skipping loot broadcast.")
            return 0

        recipients = self.load_subscribers()
        if not recipients:
            logging.info("SMTP: no subscribers in %s", SUBSCRIBERS_FILE)
            return 0

        deal_id = str(deal.get("id") or deal.get("deal_id") or "unknown")
        print(f"[EMAIL] Attempting to send deal {deal_id} to {len(recipients)} recipients", flush=True)

        title = html.escape(str(deal.get("title") or "Deal").strip())
        link = str(deal.get("affiliate_url") or deal.get("url") or "").strip()
        link_esc = html.escape(link, quote=True)
        deal_id = str(deal.get("id") or deal.get("deal_id") or link[-24:] or "unknown")

        if not link:
            logging.warning("SMTP: missing affiliate/url for deal_id=%s; skipping.", deal_id)
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
            logging.error("SMTP: empty/invalid HTML body; aborting broadcast.")
            return 0

        sent = 0
        context = ssl.create_default_context()
        
        for to_addr in recipients:
            try:
                msg = MIMEMultipart("alternative")
                msg["From"] = self.from_email
                msg["To"] = to_addr
                msg["Subject"] = f"Loot: {title[:60]}"
                
                part1 = MIMEText(f"Loot Alert: {title}\nBuy Now: {link}", "plain")
                part2 = MIMEText(html_body, "html")
                
                msg.attach(part1)
                msg.attach(part2)
                
                with smtplib.SMTP(self.host, self.port) as server:
                    server.starttls(context=context)
                    server.login(self.user, self.password)
                    text = msg.as_string()
                    server.sendmail(self.from_email, to_addr, text)
                
                print(f"[SMTP] to={to_addr} status=success", flush=True)
                sent += 1
            except Exception as e:
                if "535" in str(e):
                    print(f"[CRITICAL] SMTP 535 Authentication Failed: Check EMAIL_USER and EMAIL_PASS (use App Password for Gmail)", flush=True)
                logging.warning("SMTP send failed for %s: %s", to_addr, e)

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
        if not self.from_email:
            raise ValueError("EMAIL_USER is missing")
        if not self.password:
            logging.info("SMTP: EMAIL_PASS not set; skipping daily loot broadcast.")
            return 0

        recipients = self.load_subscribers()
        if not recipients:
            logging.info("SMTP: no subscribers in %s", SUBSCRIBERS_FILE)
            return 0

        top = []
        for d in deals[:12]:
            t = html.escape(str(d.get("title") or "Deal"))
            u = str(d.get("affiliate_url") or d.get("url") or "").strip()
            if not u:
                continue
            top.append((t, html.escape(u, quote=True)))

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

        sent = 0
        context = ssl.create_default_context()
        
        for to_addr in recipients:
            try:
                msg = MIMEMultipart("alternative")
                msg["From"] = self.from_email
                msg["To"] = to_addr
                msg["Subject"] = subject
                
                plain_text = "Daily Loot:\n" + "\n".join([f"{t}: {u}" for t, u in top])
                part1 = MIMEText(plain_text, "plain")
                part2 = MIMEText(html_body, "html")
                
                msg.attach(part1)
                msg.attach(part2)
                
                with smtplib.SMTP(self.host, self.port) as server:
                    server.starttls(context=context)
                    server.login(self.user, self.password)
                    text = msg.as_string()
                    server.sendmail(self.from_email, to_addr, text)
                
                print(f"[SMTP] to={to_addr} status=success", flush=True)
                sent += 1
            except Exception as e:
                if "535" in str(e):
                    print(f"[CRITICAL] SMTP 535 Authentication Failed: Check EMAIL_USER and EMAIL_PASS (use App Password for Gmail)", flush=True)
                logging.warning("SMTP send failed for %s: %s", to_addr, e)

        if sent:
            _log_broadcast("daily_loot", sent)
        if sent == len(recipients):
            print(f"[EMAIL:SUCCESS] Sent to {sent} subscribers", flush=True)
        else:
            print(f"[EMAIL:PARTIAL] Sent to {sent}/{len(recipients)} subscribers", flush=True)
        return sent

    def send_immediate_alert(self, deal: dict) -> int:
        """
        Immediate send path: no discount threshold gate.
        Prints SMTP status for every attempt.
        """
        pct = float(deal.get("discount_pct") or deal.get("discount_percentage") or 0.0)
        return self.broadcast_loot_deal(deal, pct)
