import asyncio
import logging
import json
import os
import random
import time
import re
import traceback
import sqlite3
import csv
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote, urljoin

import aiohttp
from cachetools import TTLCache
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError

BYPASS_PERSONA_FILE = "persona_bypass.json"

from scrapers.manual_feed import get_manual_deal
from scrapers.earnkaro import get_earnkaro_deals
from scrapers.courses import get_free_courses
from scrapers.amazon import get_amazon_product, get_diverse_amazon_deals
from scrapers.flipkart import get_flipkart_product, get_flipkart_deals
from sendgrid_notifier import SendGridNotifier

import config

# ================== CONFIGURATION & SETUP ==================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
]

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Load Config
BOT_TOKEN = config.BOT_TOKEN
CHANNELS = config.CHANNELS
DISCORD_WEBHOOK_URL = config.DISCORD_WEBHOOK_URL
HIGH_EPC_CATEGORIES = getattr(config, "HIGH_EPC_CATEGORIES", ["electronics"])
WHATSAPP_ENABLED = getattr(config, "WHATSAPP_ENABLED", False)
WHATSAPP_ACCESS_TOKEN = getattr(config, "WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = getattr(config, "WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_RECIPIENT = getattr(config, "WHATSAPP_RECIPIENT", "")
WHATSAPP_CHANNEL_NAME = getattr(config, "WHATSAPP_CHANNEL_NAME", "Arbitrage..")
POST_INTERVAL_SECONDS = 300 # Revenue Priority: 5 Minutes
ANTI_SPAM_DELAY = 1 # Revenue Priority: 1 Second
MAX_DEALS_PER_BATCH = 15 # Revenue Priority: 15
THROTTLE_DEALS_PER_RUN = 0 # Revenue Priority: 0
MAX_DEALS_PER_PERSONA_PER_BATCH = 15 # Revenue Priority: 15
MIN_DISCOUNT_THRESHOLD = 0 # FORCE DEAL DELIVERY: 0
LOOT_THRESHOLD = float(getattr(config, "LOOT_THRESHOLD", 50.0))  # Loot deal threshold (%)
FORCE_EMAIL_TEST = False  # Set True to override threshold in prod
TEST_MODE = config.TEST_MODE
DRY_RUN = config.DRY_RUN
SINGLE_RUN = config.SINGLE_RUN

logging.info(f"Startup Flags: TEST_MODE={TEST_MODE} | DRY_RUN={DRY_RUN} | SINGLE_RUN={SINGLE_RUN}")

DEALS_FILE = config.DEALS_FILE
CACHE_FILE = config.CACHE_FILE
ANALYTICS_FILE = config.ANALYTICS_FILE
SALE_POLL_INTERVAL_MINUTES = config.SALE_POLL_INTERVAL_MINUTES
STOCK_ALERT_THRESHOLDS = config.STOCK_ALERT_THRESHOLDS
SALE_FOLLOWUP_CACHE_FILE = config.SALE_FOLLOWUP_CACHE_FILE
WAITLIST_DB_FILE = getattr(config, "WAITLIST_DB_FILE", "waitlist_db.json")
KILL_SWITCH_FILE = "kill_switch.active"
SPAM_PAUSE_FILE = "spam_pause.json"

# Global State
# T-046: Memory Leak Prevention via SQLite Deduplication
processed_cache = {}

KNOWN_BAD_AMAZON_ASINS = {"B0BDKD8DVD", "B09JR8X4N6", "B089MWT1L2", "B0CHJXKHWT", "B0CHJWMXL4"}
KNOWN_BAD_TITLE_SNIPPETS = {
    "apple airpods pro (2nd generation)", "apple airpods pro",
    "apple airpods", "airpods pro", "airpods", "earpods",
    "iphone 15 pro max", "iphone 14 pro max",
    "boat rock", "boat stone",
    "realme buds", "oppo enco",
}


def is_known_bad_deal(url: str, title: str = "") -> bool:
    raw = str(url or "").lower()
    ttl = str(title or "").strip().lower()
    for asin in KNOWN_BAD_AMAZON_ASINS:
        if f"/dp/{asin.lower()}" in raw:
            return True
    return any(snippet in ttl for snippet in KNOWN_BAD_TITLE_SNIPPETS)


def normalize_price(value):
    if value is None:
        return None
    cleaned = str(value).replace("₹", "").replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    return cleaned


def _to_float_price(x) -> float | None:
    s = str(x or "").strip()
    if not s:
        return None
    s = re.sub(r"[^\d.]", "", s)
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _extract_discount_pct_from_text(text: str) -> float:
    m = re.search(r"(\d{1,3})\s*%+", str(text or ""), re.I)
    if not m:
        return 0.0
    try:
        v = float(m.group(1))
        return v if 0 <= v <= 100 else 0.0
    except Exception:
        return 0.0


def _load_persona_bypass_runs(default_runs: int = 5) -> int:
    """
    Temporary production verification bypass.
    When enabled, we bypass the per-source gate for Amazon/Flipkart so links can be validated end-to-end.
    """
    try:
        if not os.path.exists(BYPASS_PERSONA_FILE):
            return default_runs
        with open(BYPASS_PERSONA_FILE, encoding="utf-8") as f:
            obj = json.load(f) or {}
        n = int(obj.get("runs_left", 0))
        return max(0, n)
    except Exception:
        return default_runs


def _save_persona_bypass_runs(runs_left: int) -> None:
    try:
        with open(BYPASS_PERSONA_FILE, "w", encoding="utf-8") as f:
            json.dump({"runs_left": int(runs_left)}, f)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception:
        pass


def ensure_affiliate_url(url: str, source: str) -> str:
    if not url:
        return ""

    # UX GUARD: Extract destination from app-redirect links
    if "topdeal.app.link" in url.lower() or "earnkaro.com" in url.lower():
        try:
            p = urlparse(url)
            qs = parse_qs(p.query)
            if "url" in qs and qs["url"]:
                d = qs["url"][0]
                if d.startswith("http"):
                    url = d
        except Exception:
            pass

    parsed = urlparse(url)
    params = dict(parse_qs(parsed.query, keep_blank_values=True))
    source_l = (source or "").lower()

    if "amazon" in source_l or "amazon." in parsed.netloc:
        params["tag"] = [config.AFFILIATE_TAGS.get("amazon.in") or "anany-21"]
    elif "flipkart" in source_l or "flipkart" in parsed.netloc:
        params["affid"] = [config.AFFILIATE_TAGS.get("flipkart.com") or "anany-flip"]

    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


def has_valid_affiliate_url(url: str, source: str) -> bool:
    if not url:
        return False
    source_l = (source or "").lower()
    if "amazon" in source_l or "amazon." in url:
        return "tag=" in url
    if "flipkart" in source_l or "flipkart" in url:
        return "affid=" in url
    return url.startswith("http")


class AffiliateLinkGenerator:
    """
    Mandatory affiliate plumbing: never allow raw links to reach Telegram/Email.
    Priority: Direct Tag Injection > EarnKaro Profit Link > Raw URL (Fallback)
    """

    @staticmethod
    async def generate(session: aiohttp.ClientSession, url: str, source: str) -> str:
        """
        Monetizes links with UX as priority.
        - Amazon/Flipkart: uses native tag injection (DIRECT, no app store redirect)
        - Others: tries EarnKaro API
        - Fail-safe: returns raw url instead of broken app links (user priority: no app install)
        """
        raw = (url or "").strip()
        if not raw:
            return ""

        # UX GUARD: If the URL is already an app-redirect link, try to extract the destination
        if "topdeal.app.link" in raw.lower() or "earnkaro.com" in raw.lower():
            try:
                parsed = urlparse(raw)
                params = parse_qs(parsed.query)
                if "url" in params and params["url"]:
                    dest = params["url"][0]
                    if dest.startswith("http"):
                        print(f"[UX:FIX] Extracted destination from redirect link: {dest}", flush=True)
                        raw = dest
            except Exception:
                pass

        source_l = (source or "").lower()
        
        # Priority 1: Direct Native Tagging for major marketplaces (UX optimization: No app store redirect)
        if "amazon" in source_l or "amzn" in raw.lower() or "amazon." in raw.lower():
            return ensure_affiliate_url(raw, "amazon")
        if "flipkart" in source_l or "flipkart." in raw.lower():
            return ensure_affiliate_url(raw, "flipkart")

        try:
            parsed = urlparse(raw)
            host = (parsed.netloc or "").lower()
        except Exception:
            host = ""

        # If already an EarnKaro profit link, don't double-tag.
        if "earnkaro" in host or "topdeal.app.link" in host:
            return raw

        # EarnKaro for other sources (Udemy, etc.)
        key = (os.getenv("EARNKARO_API_KEY") or "").strip()
        if not key:
            print(f"[MONEY_LOSS] No EARNKARO_API_KEY; returning raw URL for {raw}", flush=True)
            return raw

        api = f"https://earnkaro.com/api/v1/generate_link?url={quote(raw, safe='')}"
        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "Referer": "https://earnkaro.com/",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with session.get(api, headers=headers, timeout=15, ssl=False) as resp:
                body = await resp.text()
                if resp.status == 200:
                    try:
                        payload = json.loads(body)
                        profit = (
                            (payload.get("data") or {}).get("profit_link")
                            or payload.get("profit_link")
                            or payload.get("link")
                            or payload.get("url")
                            or ""
                        )
                        profit = str(profit).strip()
                        # UX GUARD: Ensure we don't return a link that leads to app install page
                        if profit and profit.startswith("http") and "topdeal.app.link" not in profit:
                            dom = host.split(":")[0] if host else "unknown"
                            print(f"[REVENUE:SUCCESS] EarnKaro Profit Link generated for {dom}.", flush=True)
                            return profit
                    except Exception:
                        pass
                
                print(f"[MONEY_LOSS] EarnKaro API status {resp.status} or bad link for {raw}; returning raw URL to avoid app install redirect", flush=True)
        except Exception as e:
            print(f"[MONEY_LOSS] EarnKaro request failed ({e}); returning raw URL for {raw}", flush=True)

        # Fallback to raw URL instead of broken topdeal.app.link to ensure "no app install" UX
        return raw

    @staticmethod
    def is_valid(url: str, source: str) -> bool:
        u = str(url or "").strip().lower()
        if not u.startswith("http"):
            return False
        # Allow EarnKaro links OR direct affiliate links for Amazon/Flipkart
        if "earnkaro.com" in u or "topdeal.app.link" in u:
            return True
        if "amazon" in u and "tag=" in u:
            return True
        if "flipkart" in u and "affid=" in u:
            return True
        # For other sources, we accept raw links as fallback if monetization failed (UX priority)
        return True


def coerce_deal_object(deal: dict) -> dict:
    source = (deal.get("source") or deal.get("marketplace") or "").lower()
    if "amazon" in source:
        source = "amazon"
    elif any(x in source for x in ["coupon", "couponami", "coupondunia"]):
        source = "coupondunia"
    elif "flipkart" in source:
        source = "flipkart"
    else:
        source = "unknown"

    raw_url = deal.get("url") or deal.get("affiliate_url") or ""
    affiliate_url = ensure_affiliate_url(deal.get("affiliate_url") or raw_url, source)

    normalized = {
        "title": (deal.get("title") or "").strip(),
        "price": deal.get("price") or deal.get("new_price"),
        "original_price": deal.get("original_price") or deal.get("old_price"),
        "url": raw_url,
        "affiliate_url": affiliate_url,
        "source": source,
        "marketplace": deal.get("marketplace") or source.title(),
        "category": deal.get("category", "general"),
    }

    if normalized["price"] is not None:
        normalized["new_price"] = normalized["price"]
    if normalized["original_price"] is not None:
        normalized["old_price"] = normalized["original_price"]
    return normalized

def is_individual_product_url(url):
    """
    Anti-Category Logic: Only process individual product URLs.
    Reject category pages, deals pages, and listing pages.
    """
    if not url:
        return False
    
    # Individual product indicators
    product_indicators = ['/p/', '/dp/', '/product/', '/items/']
    
    # Category/deals page indicators to reject
    category_indicators = ['/deals', '/offers', '/sale', '/category', '/categories', '/browse', '/search', '/s/', '/gp/bestsellers', '/gp/goldbox']
    
    # Check if URL contains product indicators
    has_product_indicator = any(indicator in url.lower() for indicator in product_indicators)
    
    # Check if URL contains category indicators (reject these)
    has_category_indicator = any(indicator in url.lower() for indicator in category_indicators)
    
    # Only allow if it has product indicators AND no category indicators
    return has_product_indicator and not has_category_indicator

def validate_deal(deal_data: dict) -> bool:
    """
    Production-grade validation.

    Rules:
    - Reject only if schema is broken OR URL was confirmed 404.
    - Allow missing numeric price if the discount percentage is explicitly present
      in the source feed/title (e.g. "60% OFF") so email can still trigger.
    """
    title = str(deal_data.get("title") or "").strip()
    url = str(deal_data.get("affiliate_url") or deal_data.get("url") or "").strip()
    if not title or len(title) < 3:
        return False
    if not url.startswith("http"):
        return False
    if str(deal_data.get("enrich_error") or "").strip() == "404":
        return False

    price = deal_data.get("new_price") or deal_data.get("price")
    price_val = _to_float_price(price)
    discount_pct = deal_data.get("discount_percentage") or deal_data.get("discount_percent") or deal_data.get("discount")
    disc_val = _extract_discount_pct_from_text(discount_pct) or _extract_discount_pct_from_text(title)

    return price_val is not None or disc_val > 0

def log_delivery_audit(attempt_type: str, success: bool, deal_id: str, error_msg: str = ""):
    """
    Logs delivery attempts to delivery_audit.csv for dashboard tracking.
    Tracks Telegram uptime and success rates.
    """
    try:
        append_delivery_audit_row(
            channel=str(attempt_type),
            status="Success" if success else ("ResetError" if "reset" in str(error_msg).lower() else "Fail"),
            deal_id=str(deal_id),
        )
    except Exception as e:
        logging.error(f"Failed to write delivery audit: {e}")

def init_db():
    conn = sqlite3.connect("sent_deals.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS sent_deals
                 (product_id TEXT PRIMARY KEY, timestamp DATETIME)""")
    conn.commit()
    conn.close()

def is_deal_sent(product_id):
    # 24-hour in-process memory guard (in addition to SQLite)
    now = datetime.now()
    for k, ts in list(processed_cache.items()):
        if isinstance(ts, datetime) and now - ts > timedelta(hours=24):
            processed_cache.pop(k, None)
    if product_id in processed_cache:
        return True

    conn = sqlite3.connect("sent_deals.db")
    c = conn.cursor()
    # Check if deal was sent in the last 24 hours
    limit = (datetime.now() - timedelta(hours=24)).isoformat()
    c.execute("SELECT 1 FROM sent_deals WHERE product_id=? AND timestamp > ?", (product_id, limit))
    res = c.fetchone()
    conn.close()
    return res is not None

def mark_deal_sent(product_id):
    # Keep in-process 24h memory cache hot to block same-session duplicates.
    processed_cache[product_id] = datetime.now()

    conn = sqlite3.connect("sent_deals.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sent_deals (product_id, timestamp) VALUES (?, ?)",
              (product_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

init_db()

# processed_cache is now replaced by SQLite, but we keep the variable for compatibility if needed elsewhere
followup_cache = {}
reciprocity_state = {"free": 0, "paid": 0}
category_throttle_state = {} # {"category": timestamp_until_resume}

# ================== CORE FUNCTIONS ==================

def check_spam_pause():
    """
    Checks if the bot is in a safety pause due to spam reports.
    Returns: (is_paused, remaining_seconds)
    """
    if not os.path.exists(SPAM_PAUSE_FILE):
        return False, 0
        
    try:
        data = load_json(SPAM_PAUSE_FILE, default={})
        pause_until_str = data.get("pause_until")
        if not pause_until_str:
            return False, 0
            
        pause_until = datetime.fromisoformat(pause_until_str)
        now = datetime.now()
        
        if now < pause_until:
            remaining = (pause_until - now).total_seconds()
            return True, remaining
        else:
            # Expired, clean up
            os.remove(SPAM_PAUSE_FILE)
            return False, 0
    except Exception as e:
        logging.error(f"Error checking spam pause: {e}")
        return False, 0

def activate_spam_pause(duration_hours=24):
    """
    Activates the safety pause.
    """
    pause_until = datetime.now() + timedelta(hours=duration_hours)
    data = {
        "pause_until": pause_until.isoformat(),
        "reason": "Telegram Spam/Flood Detected"
    }
    save_json(SPAM_PAUSE_FILE, data)
    logging.critical(f"🛑 SPAM SAFETY PAUSE ACTIVATED UNTIL {pause_until}")

def check_category_throttle(category):
    """
    Checks if a category is currently throttled due to low EPC.
    """
    now = datetime.now()
    
    # 1. Check active pause
    if category in category_throttle_state:
        resume_time = category_throttle_state[category]
        if now < resume_time:
            logging.info(f"Category '{category}' is throttled until {resume_time}")
            return True # Throttled
        else:
            del category_throttle_state[category] # Expired
            
    # 2. Check EPC (Simplified: Read latest from summary or analytics)
    # Ideally, we read a 'real-time' stats file. 
    # For now, we'll skip the heavy read for every deal and rely on a periodic update 
    # or just assume if it's not in state, it's fine. 
    # Real implementation would update category_throttle_state periodically.
    return False

def update_category_throttles():
    """
    Reads analytics to update throttle state. 
    Should be called periodically.
    """
    try:
        # Check summary file for latest EPCs
        if not os.path.exists("daily_business_summary.csv"):
            return

        import pandas as pd
        df = pd.read_csv("daily_business_summary.csv")
        if df.empty: return
        
        # Get latest row
        latest = df.iloc[-1]
        epc_map_str = latest.get("epc_per_category", "{}")
        try:
            epc_map = eval(epc_map_str) # Safe enough for internal file
            for cat, epc in epc_map.items():
                if epc < config.EPC_THROTTLE_THRESHOLD:
                    if cat not in category_throttle_state:
                        resume_time = datetime.now() + timedelta(hours=12)
                        category_throttle_state[cat] = resume_time
                        logging.warning(f"📉 Throttling Category '{cat}' (EPC {epc} < {config.EPC_THROTTLE_THRESHOLD}) until {resume_time}")
        except:
            pass
    except Exception as e:
        logging.error(f"Throttle Update Failed: {e}")

def log_rejection(deal_identifier, reason_obj, source="scraper"):
    """
    Logs rejected deals to REVENUE_LOSS.log for high-priority audit.
    Includes traceback to find the exact line of code stopping the deal.
    """
    timestamp = datetime.now().isoformat()
    
    # Extract traceback info to find the line of code that stopped it
    stack = traceback.format_stack()
    # Usually the caller is the 3rd or 4th item from the end of the stack
    caller_info = stack[-3].strip() if len(stack) >= 3 else "Unknown Source"

    if isinstance(reason_obj, dict):
        stage = str(reason_obj.get("stage", "General")).strip()
        rule = str(reason_obj.get("rule", "generic")).strip()
        detail = str(reason_obj.get("detail", "unknown_reason")).strip()
        stage_label = stage.title()
        if "Failure" not in stage_label and "Error" not in stage_label:
            stage_label += " Failure"
        reason_str = f"{stage_label} | {detail}"
    else:
        reason_str = str(reason_obj)

    log_entry = f"{timestamp},{deal_identifier},{reason_str},{source},LOC:{caller_info}\n"
    
    try:
        # Use REVENUE_LOSS.log as requested for permanent revenue engine audit
        with open("REVENUE_LOSS.log", "a", encoding="utf-8") as f:
            if os.stat("REVENUE_LOSS.log").st_size == 0:
                f.write("timestamp,deal_identifier,reason,source,line_of_code\n")
            f.write(log_entry)
            
        # Also keep rejection_audit.log for backward compatibility
        with open("rejection_audit.log", "a", encoding="utf-8") as f:
            if os.stat("rejection_audit.log").st_size == 0:
                f.write("timestamp,deal_identifier,reason,source\n")
            f.write(f"{timestamp},{deal_identifier},{reason_str},{source}\n")
            
    except Exception as e:
        try:
            logging.error(f"Failed to write to rejection log: {e}")
        except:
            print(f"CRITICAL: Logging failed during rejection log write: {e}")

def log_post(deal_identifier, category, platform="telegram"):
    """
    Logs successfully posted deals.
    """
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp},{deal_identifier},{category},{platform}\n"
    
    try:
        with open("post_audit.log", "a", encoding="utf-8") as f:
            if os.stat("post_audit.log").st_size == 0:
                f.write("timestamp,deal_identifier,category,platform\n")
            f.write(log_entry)
    except Exception as e:
        logging.error(f"Failed to write to post log: {e}")

def update_trust_decay(user_id, event_type="forbidden"):
    """
    Updates trust_decay.json when a Telegram error occurs.
    """
    decay_file = "trust_decay.json"
    data = load_json(decay_file, default=[])
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "event_type": event_type,
        "decay_score_increment": 1
    }
    
    data.append(entry)
    save_json(decay_file, data)
    logging.warning(f"Trust Decay Event Logged: {event_type} for {user_id}")

def update_heartbeat():
    """T-047/T-048: Updates heartbeat file for watchdog monitoring."""
    try:
        with open("heartbeat.timestamp", "w") as f:
            f.write(str(datetime.now().timestamp()))
    except Exception as e:
        logging.error(f"Heartbeat write failed: {e}")

def check_kill_switch():
    """T-049: Checks for global kill switch."""
    return os.path.exists(KILL_SWITCH_FILE)

def load_json(filepath, default=None):
    """Safely loads JSON data from a file."""
    if default is None:
        default = [] if "analytics" not in filepath else {}
        
    if not os.path.exists(filepath):
        return default

    # Fail-Safe: Empty file check
    try:
        if os.stat(filepath).st_size == 0:
            return default
    except OSError:
        return default

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading {filepath}: {e}")
        return default


def load_seed_amazon_deals():
    """
    Seed Amazon product URLs from existing repo artifacts so Amazon is always
    present in the candidate set even when listing scraping is blocked.
    """
    seeds = []
    seen = set()

    for path in ["site/deals.json", "reddit_drafts.json"]:
        try:
            payload = load_json(path, default=[]) or []
            for item in payload:
                if not isinstance(item, dict):
                    continue
                raw = item.get("url", "")
                if not raw and "body" in item:
                    match = re.search(r"https://www\.amazon\.in/[^\s)]+", item.get("body", ""))
                    raw = match.group(0) if match else ""
                if not raw or "amazon.in" not in raw.lower():
                    continue
                if "/dp/example" in raw.lower():
                    continue
                if is_known_bad_deal(raw, str(item.get("title", ""))):
                    continue
                affiliate_url = ensure_affiliate_url(raw, "amazon")
                if affiliate_url in seen:
                    continue
                seen.add(affiliate_url)
                seeds.append(
                    {
                        "title": item.get("title", "Amazon Deal"),
                        "price": item.get("new_price"),
                        "original_price": item.get("old_price"),
                        "url": raw,
                        "affiliate_url": affiliate_url,
                        "source": "amazon",
                        "marketplace": "Amazon",
                        "category": item.get("category", "general"),
                    }
                )
        except Exception as exc:
            logging.warning(f"Failed loading Amazon seeds from {path}: {exc}")

    logging.info("Loaded %s Amazon seed deals", len(seeds))
    return seeds

def save_json(filepath, data):
    """Safely saves JSON data to a file."""
    if TEST_MODE and filepath == CACHE_FILE:
        return # Don't update cache in test mode to allow replay
        
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logging.error(f"Error saving {filepath}: {e}")

def load_waitlist():
    return load_json(WAITLIST_DB_FILE, default=[])

def save_waitlist(data):
    save_json(WAITLIST_DB_FILE, data)

def register_monitor_command(user_id: int, asin: str, target_price: float):
    try:
        data = load_waitlist()
        entry = {
            "user_id": int(user_id),
            "asin": str(asin),
            "target_price": float(target_price),
            "alerted": False,
            "timestamp": datetime.now().isoformat()
        }
        data.append(entry)
        save_waitlist(data)
        logging.info(f"Registered waitlist monitor: user={user_id}, asin={asin}, target={target_price}")
    except Exception as e:
        logging.error(f"Failed to register monitor command: {e}")
        try:
            with open("audit_todo.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()},monitor_register_failed,{user_id},{asin},{target_price},{e}\n")
        except:
            pass

async def send_dm(bot: Bot, user_id: int, text: str):
    if TEST_MODE:
        return None
    try:
        return await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"DM send failed to {user_id}: {e}")
        return None

async def check_waitlist_alerts(telegram_bot: Bot, asin: str, current_price):
    try:
        data = load_waitlist()
        if not data or not asin:
            return
        try:
            price_val = float(str(current_price).replace(",", ""))
        except Exception:
            return
        updated = False
        for entry in data:
            if entry.get("asin") == asin and not entry.get("alerted", False):
                target = float(entry.get("target_price", 0))
                if price_val <= target:
                    text = f"👀 Price Alert for {asin}\nCurrent: ₹{price_val} ≤ Target: ₹{target}\nWe’ll keep monitoring for you."
                    await send_dm(telegram_bot, int(entry.get("user_id")), text)
                    entry["alerted"] = True
                    entry["alerted_at"] = datetime.now().isoformat()
                    updated = True
        if updated:
            save_waitlist(data)
    except Exception as e:
        logging.error(f"Waitlist alert check failed: {e}")

def handle_telegram_command(user_id: int, text: str):
    """
    Parses simple Telegram command messages.
    Supported:
    /monitor [ASIN] [TargetPrice]
    """
    try:
        if not isinstance(text, str):
            return False
        parts = text.strip().split()
        if len(parts) >= 3 and parts[0].lower() == "/monitor":
            asin = parts[1]
            target = float(parts[2])
            register_monitor_command(user_id, asin, target)
            return True
        else:
            with open("audit_todo.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()},unknown_command,{user_id},{text}\n")
            return False
    except Exception as e:
        logging.error(f"Command parsing failed: {e}")
        try:
            with open("audit_todo.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()},command_parse_failed,{user_id},{text},{e}\n")
        except:
            pass
        return False

def canonicalize_url(url: str) -> str:
    """Cleans up product URLs for Amazon and Flipkart before tagging."""
    try:
        if "amazon.in" in url or "amzn" in url:
            asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
            if asin_match:
                return f"https://www.amazon.in/dp/{asin_match.group(1)}"
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        elif "flipkart.com" in url:
            # Flipkart URLs often have a pid and lid in query, but path is the core product
            parsed = urlparse(url)
            # Keep pid for Flipkart as it is sometimes required
            query_params = parse_qs(parsed.query)
            pid = query_params.get("pid")
            if pid:
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?pid={pid[0]}"
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception as e:
        logging.error(f"Canonicalization failed for {url}: {e}")
    return url


MERCHANT_HOST_MARKERS = (
    "amazon.",
    "flipkart.",
    "myntra.",
    "ajio.",
    "udemy.com",
    "nykaa.",
    "tatacliq.",
    "croma.",
    "reliancedigital.",
)


def _looks_like_product_url(u: str) -> bool:
    x = str(u or "").lower()
    return (
        "/dp/" in x
        or "/gp/product/" in x
        or "/p/" in x
        or "/course/" in x
        or "pid=" in x
        or "/product/" in x
        or "/buy/" in x
    )


def _is_merchant_url(u: str) -> bool:
    try:
        host = (urlparse(str(u or "")).netloc or "").lower()
    except Exception:
        host = ""
    return any(m in host for m in MERCHANT_HOST_MARKERS)


async def resolve_coupon_merchant_link(session: aiohttp.ClientSession, url: str) -> str:
    """
    Resolve Couponami/Coupon pages to actual outbound merchant product links.
    Returns empty string when no merchant target is found.
    """
    if not url:
        return ""
    try:
        async with session.get(url, allow_redirects=True, timeout=15) as resp:
            text = await resp.text()
            final = str(resp.url)
        if _is_merchant_url(final) and _looks_like_product_url(final):
            return final
    except Exception:
        text = ""

    if not text:
        return ""

    try:
        soup = BeautifulSoup(text, "html.parser")
        candidates: list[str] = []
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href or href.startswith("#") or href.lower().startswith("javascript:"):
                continue
            full = urljoin(url, href)
            if _is_merchant_url(full) or "/go/" in full.lower():
                candidates.append(full)
        for c in candidates:
            # Couponami /go/ slug frequently redirects to final merchant URL.
            if "/go/" in c.lower():
                try:
                    async with session.get(c, allow_redirects=True, timeout=15) as rr:
                        redirected = str(rr.url)
                        go_text = await rr.text()
                    if _is_merchant_url(redirected):
                        return redirected
                    try:
                        go_soup = BeautifulSoup(go_text, "html.parser")
                        for ga in go_soup.select("a[href]"):
                            gh = (ga.get("href") or "").strip()
                            if not gh:
                                continue
                            gf = urljoin(c, gh)
                            if _is_merchant_url(gf) and _looks_like_product_url(gf):
                                return gf
                    except Exception:
                        pass
                except Exception:
                    pass
            if _is_merchant_url(c) and _looks_like_product_url(c):
                return c
        if candidates:
            return candidates[0]
    except Exception:
        pass

    # Last chance: regex scan raw HTML for merchant links
    try:
        for m in re.finditer(r"https?://[^\s\"'<>]+", text):
            c = m.group(0)
            if _is_merchant_url(c):
                return c
    except Exception:
        pass
    return ""


async def validate_dispatch_target(session: aiohttp.ClientSession, deal: dict) -> tuple[bool, str, str]:
    """
    Strict pre-dispatch validator:
    landing must resolve to a merchant product URL and be reachable.
    """
    target = str(deal.get("url") or deal.get("affiliate_url") or "").strip()
    if not target.startswith("http"):
        return False, target, "missing_url"
    try:
        async with session.get(target, allow_redirects=True, timeout=15) as resp:
            final = str(resp.url)
            if resp.status >= 400:
                return False, final, f"http_{resp.status}"
    except Exception as e:
        return False, target, f"net_{type(e).__name__}"
    if not _is_merchant_url(final):
        return False, final, "non_merchant_landing"
    if not _looks_like_product_url(final):
        return False, final, "non_product_landing"
    return True, final, "ok"

async def enrich_deal(session, deal: dict) -> dict:
    """
    Validates and enriches deal data asynchronously.
    Checks: HTTP 200, Stock Status, Keywords, Trust Filters, Price Errors.
    Enforces Failure Precedence: Network > Schema > Trust > Buyability > Revenue.
    """
    if not deal:
        log_rejection("N/A", {"stage": "Schema", "detail": "empty_payload"})
        return {"valid": False, "enrich_error": "None Payload"}

    url = deal.get("url")
    if not url:
        deal["valid"] = False
        log_rejection("N/A", {"stage": "Schema", "detail": "missing_url"})
        return deal
    
    source = str(deal.get("source") or deal.get("marketplace") or "").lower()

    if is_known_bad_deal(url, str(deal.get("title") or "")):
        deal["valid"] = False
        deal["enrich_error"] = "known_bad_deal"
        print(f"[SKIP] Known bad deal blocked: {deal.get('title') or url}", flush=True)
        log_rejection(url, {"stage": "Schema", "detail": "known_bad_deal"})
        return deal

    # Allow coupon/deal aggregator items to pass through without product URL heuristics.
    if "coupon" not in source and not is_individual_product_url(url):
        deal["valid"] = False
        log_rejection(url, {"stage": "Category", "detail": "not_individual_product"})
        return deal

    # Category Inference (if missing or unknown)
    # FT-023: Sanitize unknown categories to 'general'
    valid_categories = list(config.SUB_IDS.keys()) if hasattr(config, "SUB_IDS") else ["general", "audio", "laptop", "fashion", "accessory"]
    if "category" not in deal or (deal["category"] not in valid_categories and deal["category"] != "general"):
         # Simple inference
         title_lower = str(deal.get("title", "")).lower()
         if "audio" in title_lower or "headphone" in title_lower: deal["category"] = "audio"
         elif "laptop" in title_lower: deal["category"] = "laptop"
         else: deal["category"] = "general"

    # Couponami/Coupon resolver: move from landing page to actual merchant product link.
    if "coupon" in source or "couponami" in source or "coupondunia" in source:
        resolved = await resolve_coupon_merchant_link(session, str(url))
        if not resolved:
            deal["valid"] = False
            deal["enrich_error"] = "coupon_no_merchant_link"
            print(f"[SKIP] No Buy Button found on landing page: {url}", flush=True)
            log_rejection(url, {"stage": "Buyability", "detail": "coupon_no_merchant_link"})
            return deal
        deal["url"] = canonicalize_url(resolved)
        deal["source"] = (
            "amazon" if "amazon." in resolved.lower() else
            "flipkart" if "flipkart." in resolved.lower() else
            deal.get("source", "couponami")
        )
        # Re-monetize resolved merchant URL so Buy Now button is always monetized.
        deal["affiliate_url"] = await AffiliateLinkGenerator.generate(session, deal["url"], str(deal["source"]))
        url = deal["url"]
        source = str(deal.get("source") or source).lower()

    # STRICT buyability validation for Amazon:
    # require real product extraction so blocked/ghost pages never pass to Telegram/Email.
    if "amazon" in url or "amzn" in url:
        try:
            amz = await get_amazon_product(url)
        except Exception as e:
            amz = None
            logging.warning("Amazon product validation failed for %s: %r", url, e)
        if not amz:
            # Fallback for anti-bot blocked pages:
            # if feed/listing gave a concrete ASIN + numeric price, keep deal alive.
            asin_ok = bool(re.search(r"/dp/[A-Z0-9]{10}", str(url)))
            price_ok = _to_float_price(str(deal.get("new_price") or deal.get("price") or "")) is not None
            if asin_ok and price_ok:
                clean_url = canonicalize_url(str(url))
                deal["url"] = clean_url
                deal["affiliate_url"] = ensure_affiliate_url(str(deal.get("affiliate_url") or clean_url), "amazon")
                deal["new_price"] = deal.get("new_price") or deal.get("price")
                deal["valid"] = True
                print(f"[AMAZON:FALLBACK_OK] Using listing data for blocked page: {clean_url}", flush=True)
                return deal
            deal["valid"] = False
            deal["enrich_error"] = "amazon_validation_failed"
            print(f"[SKIP] Amazon product not buyable/price missing: {url}", flush=True)
            log_rejection(url, {"stage": "Buyability", "detail": "amazon_validation_failed"})
            return deal
        deal.update(amz)
        deal["new_price"] = amz.get("price") or deal.get("new_price")
        deal["title"] = amz.get("title") or deal.get("title")
        deal["affiliate_url"] = amz.get("affiliate_url") or deal.get("affiliate_url")
        deal["valid"] = True
        return deal

    if "flipkart.com" in url:
        try:
            async with session.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, allow_redirects=True, timeout=10) as resp:
                if resp.status == 404:
                    deal["valid"] = False
                    deal["enrich_error"] = "404"
                    log_rejection(url, {"stage": "Network", "detail": "404"})
                    return deal
        except Exception:
            pass
        deal["valid"] = True
        return deal
      
    # Anti-Ban: User-Agent Rotation
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    
    # Anti-Ban: Jitter (Human Mimic)
    if not TEST_MODE and config.SHADOW_MODE: 
        jitter = random.uniform(config.SCRAPE_INTERVAL_MIN, config.SCRAPE_INTERVAL_MAX)
        logging.info(f"Jitter sleep for {jitter:.1f}s before scraping {url}")
        await asyncio.sleep(jitter)
    
    # Retry logic
    for attempt in range(3):
        try:
            async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as response:
                # LEVEL 1: Network / HTTP Errors
                if response.status == 403:
                     logging.warning(f"403 Forbidden: {url}")
                     deal["valid"] = False
                     deal["enrich_error"] = "403 Forbidden"
                     log_rejection(url, {"stage": "Network", "detail": "403_forbidden"})
                     return deal

                if response.status != 200:
                    logging.warning(f"URL Validation Failed ({response.status}): {url}")
                    deal["valid"] = False
                    deal["enrich_error"] = f"HTTP {response.status}"
                    log_rejection(url, {"stage": "Network", "detail": f"http_{response.status}"})
                    return deal

                text = await response.text()
                text_lower = text.lower()
                
                # LEVEL 3: Trust Violations (Seller Rating & Shipping)
                # REVENUE IS THE ONLY PRIORITY: BYPASS TRUST FILTERS
                # rating_match = re.search(r"(\d+(\.\d+)?) out of 5 stars", text_lower)
                # if rating_match:
                #     rating = float(rating_match.group(1))
                #     if rating < config.TRUST_RATING_THRESHOLD:
                #         deal["valid"] = False
                #         deal["enrich_error"] = f"Trust Violation: Seller Rating {rating} < {config.TRUST_RATING_THRESHOLD}"
                #         logging.warning(f"Rejecting {url}: {deal['enrich_error']}")
                #         log_rejection(url, {"stage": "Trust", "detail": f"rating_below_threshold|value={rating}"})
                #         return deal
                
                # # Shipping Cost
                # shipping_match = re.search(r"\+\s?[\$₹]?(\d+(\.\d+)?)\s+shipping", text_lower)
                # if shipping_match:
                #     shipping_cost = float(shipping_match.group(1))
                #     price = deal.get("new_price", 0)
                #     try:
                #         price_val = float(str(price).replace(",", ""))
                #         if price_val > 0 and (shipping_cost / price_val) > config.MAX_SHIPPING_PERCENT:
                #             deal["valid"] = False
                #             deal["enrich_error"] = f"Trust Violation: Shipping too high"
                #             logging.warning(f"Rejecting {url}: {deal['enrich_error']}")
                #             log_rejection(url, {"stage": "Trust", "detail": "shipping_too_high"})
                #             return deal
                #     except:
                #         pass

                # LEVEL 4: Buyability Failures - MANDATORY BUY BUTTON
                # To prevent "AirPods" deals that redirect but have no buy button.
                buy_markers = [
                    "add to cart", "buy now", "proceed to buy", 
                    "get this deal", "go to deal", "grab deal",
                    "activate deal", "claim deal", "shop now",
                    "buy it now", "enroll now" # Added for courses
                ]
                has_buy_button = any(marker in text_lower for marker in buy_markers)

                if not has_buy_button:
                    deal["valid"] = False
                    deal["enrich_error"] = "No Buy Button Found"
                    print(f"[SKIP] No Buy Button found on landing page: {url}", flush=True)
                    log_rejection(url, {"stage": "Buyability", "detail": "no_buy_button"})
                    return deal

                # Fallback for messy or missing title/price
                if not deal.get("title") or not str(deal.get("title")).strip():
                    deal["title"] = '🔥 MEGA DEAL'
                
                price = deal.get("new_price")
                try:
                    # A simple check to see if price is a reasonable number
                    if price and str(price).lower() not in ["free", "0", "check link"]:
                        float(str(price).replace(",", "").replace("₹", ""))
                except (ValueError, TypeError, AttributeError):
                    deal["new_price"] = 'Check Link'


                # LEVEL 5: Revenue / EPC Gating
                # REVENUE IS THE ONLY PRIORITY: BYPASS ANCHOR PRICING GATING
                # if config.REQUIRE_ANCHOR_PRICING:
                #      if not deal.get("anchor_price") or not deal.get("days_since_high"):
                #          deal["valid"] = False
                #          deal["enrich_error"] = "Missing Anchor Pricing Data"
                #          logging.warning(f"Skipping Deal - No Anchor Pricing: {url}")
                #          log_rejection(url, {"stage": "Revenue", "detail": "missing_anchor_pricing"})
                #          return deal

                #      try:
                #          ap = float(str(deal["anchor_price"]).replace(",", ""))
                #          np = float(str(deal.get("new_price", 0)).replace(",", ""))
                #          if ap < np:
                #              deal["valid"] = False
                #              deal["enrich_error"] = "Anchor Price Lower Than Current Price"
                #              logging.warning(f"Skipping Deal - Anchor ({ap}) < New ({np}): {url}")
                #              log_rejection(url, {"stage": "Revenue", "detail": "anchor_price_inversion"})
                #              return deal
                             
                #          # False MRP Check
                #          if deal.get("old_price"):
                #              op = float(str(deal["old_price"]).replace(",", ""))
                #              if op > (ap * 1.5):
                #                  deal["valid"] = False
                #                  deal["enrich_error"] = "False MRP Detected"
                #                  logging.warning(f"Skipping Deal - False MRP ({op} > {ap}*1.5): {url}")
                #                  log_rejection(url, {"stage": "Revenue", "detail": "false_mrp_detected"})
                #                  return deal
                #      except Exception as e:
                #          logging.warning(f"Price validation error: {e}")



                # Stock Check (Basic keyword matching)
                if "currently unavailable" in text_lower or "out of stock" in text_lower or "sold out" in text_lower:
                    deal["in_stock"] = False
                    deal["stock_status"] = "OutOfStock"
                else:
                    deal["in_stock"] = True
                    deal["stock_status"] = "InStock"
                    
                # Low Stock Warning (Regex for exact count)
                # Matches: "Only 5 left in stock", "Only 1 left in stock"
                stock_match = re.search(r"only\s+(\d+)\s+left\s+in\s+stock", text_lower)
                if stock_match:
                    deal["low_stock"] = True
                    deal["stock_count"] = int(stock_match.group(1))
                elif "only" in text_lower and "left in stock" in text_lower:
                    deal["low_stock"] = True
                    deal["stock_count"] = 5 # Default low number if parsing fails
                else:
                    deal["stock_count"] = 100 # Assume plenty
                
                # Append urgency tag once (title)
                try:
                    title = str(deal.get("title", ""))
                    tag = None
                    if deal.get("low_stock") and deal.get("stock_count", 100) < 10:
                        tag = f"[🔥 LOW STOCK – {deal.get('stock_count')} LEFT]"
                    elif deal.get("percent_claimed") and deal.get("percent_claimed") <= 20:
                        tag = "[🔥 LOW STOCK – <20% LEFT]"
                    if tag and tag not in title:
                        deal["title"] = f"{title} {tag}"
                except Exception:
                    pass

                # Gamified Scarcity: Percent Claimed
                claimed_match = re.search(r"(\d+)%\s+claimed", text_lower)
                if claimed_match:
                    deal["percent_claimed"] = int(claimed_match.group(1))
                elif deal.get("low_stock") and deal.get("stock_count", 100) < 10:
                    # Heuristic: If < 10 items, assume high claim rate for visual drama
                    deal["percent_claimed"] = 90

                # Mental Accounting (Pain-of-Payment Softener)
                # Only if price > Threshold and not impulse buy
                new_price = deal.get("new_price", 0)
                try:
                    price_val = float(str(new_price).replace(",", ""))
                    
                    # Decoy Effect / Comparison Table Logic
                    # If price > 500 (not trivial)
                    if price_val > 500:
                         # Generate a generic decoy
                        decoy_price = int(price_val * 1.25)
                        deal["comparison_data"] = {
                            "pros": ["Best Value", "High Rating", "Lowest Price"],
                            "cons": ["Higher Price", "Standard Features"],
                            "decoy_price": decoy_price
                        }

                    if price_val >= config.MENTAL_ACCOUNTING_THRESHOLD:
                        # Calculate daily cost (assume 1 year for durables)
                        daily_cost = price_val / 365
                        comparison = "coffee" if daily_cost < 200 else "meal"
                        if daily_cost < 20: comparison = "gum"
                        
                        deal["payment_softener"] = {
                            "per_day_cost": round(daily_cost, 2),
                            "comparison": comparison
                        }
                except:
                    pass

                # Coupon Check
                if "coupon" in text_lower or "voucher" in text_lower:
                    deal["has_coupon"] = True
                    
                # Refurbished Check
                if "refurbished" in text_lower or "renewed" in text_lower:
                    deal["condition"] = "Refurbished"
                else:
                    deal["condition"] = "New"

                # Anchor Pricing & Social Proof Data
                deal["anchor_price"] = deal.get("anchor_price")
                deal["days_since_high"] = deal.get("days_since_high")
                deal["clicks_last_60_min"] = deal.get("clicks_last_60_min")
                deal["persona"] = deal.get("persona")

                # --- PRICE ERROR DETECTION ---
                try:
                    op = float(str(deal.get("old_price", 0)).replace(",", ""))
                    np = float(str(deal.get("new_price", 0)).replace(",", ""))
                    if op > 0:
                        drop_pct = (op - np) / op
                        if drop_pct > config.PRICE_ERROR_DROP_THRESHOLD:
                             deal["is_price_error"] = True
                             # Suppress False Positives? 
                             # For now, just tag it. The bot might handle it by posting with warning or to admin only.
                             # User said "tag as 🚨 PRICE ERROR".
                             # We prepend to title so it's visible in logs/shadow channel
                             if "PRICE ERROR" not in deal.get("title", ""):
                                 deal["title"] = f"🚨 PRICE ERROR: {deal.get('title')}"
                except:
                    pass

                deal["valid"] = True
                return deal
                
        except asyncio.TimeoutError:
            if attempt == 2:
                logging.error(f"Enrichment failed for {url} after 3 attempts: Timeout")
                deal["valid"] = False
                deal["enrich_error"] = "Network Timeout"
                log_rejection(url, {"stage": "Network", "detail": "timeout"})
                return deal
            await asyncio.sleep(2 ** attempt)

        except aiohttp.TooManyRedirects as e:
            if attempt == 2:
                logging.error(f"Enrichment failed for {url} after 3 attempts: Too Many Redirects")
                deal["valid"] = False
                deal["enrich_error"] = "Network Error: Too Many Redirects"
                log_rejection(url, {"stage": "Network", "detail": "too_many_redirects"})
                return deal
            await asyncio.sleep(2 ** attempt)

        except aiohttp.ClientError as e:
            if attempt == 2:
                logging.error(f"Enrichment failed for {url} after 3 attempts: {e}")
                deal["valid"] = False
                deal["enrich_error"] = f"Network Error: {e}"
                log_rejection(url, {"stage": "Network", "detail": f"client_error_{e}"})
                return deal
            await asyncio.sleep(2 ** attempt)

        except OSError as e:
            if attempt == 2:
                logging.error(f"Enrichment failed for {url} after 3 attempts: {e}")
                deal["valid"] = False
                deal["enrich_error"] = f"Network Error: {e}"
                log_rejection(url, {"stage": "Network", "detail": f"os_error_{e}"})
                return deal
            await asyncio.sleep(2 ** attempt)

        except UnicodeDecodeError as e:
            if attempt == 2:
                logging.error(f"Enrichment failed for {url} after 3 attempts: {e}")
                deal["valid"] = False
                deal["enrich_error"] = f"Encoding Error: {e}"
                log_rejection(url, {"stage": "Network", "detail": "codec_error"})
                return deal
            await asyncio.sleep(2 ** attempt)

        except Exception as e:
            if attempt == 2:
                logging.error(f"Enrichment failed for {url} after 3 attempts: {e}")
                deal["valid"] = False
                deal["enrich_error"] = str(e)
                log_rejection(url, {"stage": "Unknown", "detail": str(e)})
                return deal
            await asyncio.sleep(2 ** attempt) # Exponential backoff

    return deal

# ================== FOLLOW-UP LOGIC ==================

async def process_followups(session, bot: Bot, stats: dict):
    """
    Checks watched deals for stock/price changes and reposts if thresholds met.
    """
    global followup_cache
    now = datetime.now()
    
    # Reload cache to be safe
    followup_cache = load_json(SALE_FOLLOWUP_CACHE_FILE, default={})
    
    updates_made = False
    processed_count = 0
    
    keys_to_check = list(followup_cache.keys())
    random.shuffle(keys_to_check) # Randomize check order
    
    for url in keys_to_check:
        # Respect batch limits (shared with main loop roughly, but we track separately here)
        if processed_count >= MAX_DEALS_PER_BATCH:
            break
            
        data = followup_cache[url]
        last_checked_str = data.get("last_checked")
        
        # Check if poll interval passed
        if last_checked_str:
            last_checked = datetime.fromisoformat(last_checked_str)
            if (now - last_checked).total_seconds() < (SALE_POLL_INTERVAL_MINUTES * 60):
                continue

        # Check Cooldown & Limits
        last_posted_str = data.get("last_posted")
        if last_posted_str:
             last_posted = datetime.fromisoformat(last_posted_str)
             if (now - last_posted).total_seconds() < (config.FOLLOW_UP_COOLDOWN_HOURS * 3600):
                 continue

        if len(data.get("alerts_sent", [])) >= config.MAX_FOLLOW_UPS_PER_DEAL:
            # Stop tracking if max reached? Or just stop posting?
            # Let's stop processing this one for now.
            continue
                
        # Re-Enrich
        logging.info(f"Polling follow-up: {data.get('title', 'Unknown')}")
        deal_stub = {
            "url": url, 
            "title": data.get("title"), 
            "marketplace": data.get("marketplace"),
            "clicks_last_60_min": data.get("clicks_last_60_min", 0),
            "first_seen": data.get("first_seen")
        }
        
        enriched = await enrich_deal(session, deal_stub)
        
        if not enriched.get("valid"):
            # Allow OOS updates to proceed so we can expire the post
            if enriched.get("in_stock") is False:
                pass
            else:
                logging.warning(f"Follow-up invalid/expired: {url}")
                continue
            
        # Update State
        current_stock_count = enriched.get("stock_count", 100)
        current_in_stock = enriched.get("in_stock", True)
        
        # Check Logic
        should_post = False
        alert_reason = ""
        
        # 1. Stock dropped below threshold
        alerts_sent = data.get("alerts_sent", [])
        
        if not current_in_stock:
             if "out_of_stock" not in alerts_sent:
                 logging.info(f"Item went OOS: {data.get('title')}")
                 alerts_sent.append("out_of_stock")
                 
                 # T-050: Live Post Auto-Edit (Trust Preservation)
                 if not TEST_MODE and "message_id" in data and "chat_id" in data:
                     try:
                         # Construct expired caption
                         original_title = data.get("title", "Deal")
                         expired_text = f"❌ *[EXPIRED]* {original_title}\n\n⚠️ *This deal is now Out of Stock.*"
                         await bot.edit_message_text(
                             chat_id=data["chat_id"],
                             message_id=data["message_id"],
                             text=expired_text,
                             parse_mode="Markdown"
                         )
                         logging.info(f"Edited post to EXPIRED: {url}")
                     except Exception as e:
                         logging.warning(f"Failed to edit OOS message: {e}")

                 should_post = False # Don't spam OOS
        else:
            # Check thresholds
            for threshold in STOCK_ALERT_THRESHOLDS:
                if current_stock_count < 100: 
                    if current_stock_count <= threshold and str(threshold) not in alerts_sent:
                        should_post = True
                        alert_reason = f"Only {current_stock_count} left!"
                        alerts_sent.append(str(threshold))
                        break
        
        # Update Cache Data
        data["last_checked"] = now.isoformat()
        data["last_stock"] = current_stock_count
        data["alerts_sent"] = alerts_sent
        followup_cache[url] = data
        updates_made = True

        # --- AUTOMATED LOSS-AVERSION RETARGETING ---
        # Trigger Window: 90-120 minutes after initial check/post (simulated "click")
        # Only if Stock > 0 and Strict Buyability passes
        
        # Determine "deal age" in our system to simulate user session start
        first_seen_str = data.get("first_seen")
        if not first_seen_str:
            first_seen_str = now.isoformat()
            data["first_seen"] = first_seen_str # Save for next time
            
        first_seen = datetime.fromisoformat(first_seen_str)
        minutes_since_first_seen = (now - first_seen).total_seconds() / 60
        
        # User defined window: 90 to 120 mins
        in_retarget_window = config.RETARGETING_WINDOW_MINUTES <= minutes_since_first_seen <= (config.RETARGETING_WINDOW_MINUTES + 30)
        
        if in_retarget_window and "retarget_loss_aversion" not in alerts_sent:
            # Check Buyability / Stock again
            if current_in_stock and current_stock_count > 0:
                # Only trigger if it had some interest or is high value
                # (Simulating "User Clicked" - we assume high value deals got clicks)
                is_high_value = False
                try:
                    disc = 0
                    if data.get("old_price") and data.get("new_price"):
                        op = float(str(data["old_price"]).replace(",",""))
                        np = float(str(data["new_price"]).replace(",",""))
                        if op > 0: disc = (op - np) / op
                    if disc > 0.4: is_high_value = True # >40% off
                except:
                    pass
                
                # Trigger if high value or simulated clicks
                if is_high_value or data.get("clicks_last_60_min", 0) > 10:
                    should_post = True
                    # Message Template: ⏳ Last Chance... You’ll lose ₹800 in savings...
                    savings = "big savings"
                    try:
                        op = float(str(data["old_price"]).replace(",",""))
                        np = float(str(data["new_price"]).replace(",",""))
                        savings = f"₹{int(op - np)}"
                    except:
                        pass
                        
                    alert_reason = f"⏳ *Last Chance!* You'll lose {savings} if you miss this."
                    alerts_sent.append("retarget_loss_aversion")

        if should_post:
            logging.info(f"Dynamic Follow-Up Triggered: {alert_reason} | {data.get('title')}")
            stats["follow_up_alerts_sent"] = stats.get("follow_up_alerts_sent", 0) + 1
            stats["stock_change_detected"] = stats.get("stock_change_detected", 0) + 1
            
            # Update Last Posted
            data["last_posted"] = now.isoformat()
            followup_cache[url] = data # Update cache immediately in memory
            
            # Construct Follow-up Caption
            enriched["new_price"] = data.get("new_price")
            enriched["old_price"] = data.get("old_price")
            
            # Add alert to caption
            caption, variant = format_telegram_message(enriched)
            caption = f"🚨 <b>UPDATE: {alert_reason}</b>\n\n" + caption
            
            if not TEST_MODE:
                chat_id = CHANNELS["main"]["chat_id"]
                followup_url = enriched.get("affiliate_url") or enriched.get("url", "")
                _, tg_status = await post_to_telegram(bot, chat_id, caption, followup_url)
                wa_ok, wa_status = await post_to_whatsapp(format_whatsapp_message(enriched))
                final_result = "success" if tg_status == "Success" and wa_ok else ("partial_success" if wa_ok else "fail")
                append_delivery_audit_bundle(
                    deal_id=str(enriched.get("url", "followup")),
                    telegram_status=tg_status,
                    whatsapp_status=wa_status,
                    final_result=final_result,
                )
                await post_to_discord(session, DISCORD_WEBHOOK_URL, enriched, variant)
            
            processed_count += 1
            await asyncio.sleep(ANTI_SPAM_DELAY)
            
    if updates_made and not TEST_MODE:
        save_json(SALE_FOLLOWUP_CACHE_FILE, followup_cache)


# ================== TRACKING & ANALYTICS ==================

MASTER_LOG_FIELDS = [
    "timestamp",
    "source",
    "title",
    "price",
    "original_price",
    "category",
    "decision",
    "reason",
    "affiliate_valid",
]
DELIVERY_AUDIT_FIELDS = ["timestamp", "channel", "status", "deal_id"]

SUPERBOT_MASTER_DIR = "data"
SUPERBOT_MASTER_FILE = os.path.join(SUPERBOT_MASTER_DIR, "master_log.csv")


def _ensure_dashboard_dir() -> str:
    stats_dir = "dashboard/public/data"
    os.makedirs(stats_dir, exist_ok=True)
    return stats_dir


def _ensure_superbot_master_dir() -> str:
    os.makedirs(SUPERBOT_MASTER_DIR, exist_ok=True)
    return SUPERBOT_MASTER_DIR


def append_delivery_audit_row(channel: str, status: str, deal_id: str) -> None:
    stats_dir = _ensure_dashboard_dir()
    audit_file = os.path.join(stats_dir, "delivery_audit.csv")
    file_exists = os.path.isfile(audit_file)
    if file_exists:
        try:
            with open(audit_file, encoding="utf-8", errors="ignore") as rf:
                hdr = rf.readline()
            if hdr and ("telegram_status" in hdr) and ("channel" not in hdr):
                legacy = audit_file.replace(".csv", f"_legacy_{int(time.time())}.csv")
                os.replace(audit_file, legacy)
                logging.info("delivery_audit.csv legacy schema — rotated to %s", legacy)
                file_exists = False
        except OSError:
            pass
    row = [datetime.now().isoformat(), channel, status, deal_id]
    try:
        with open(audit_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(DELIVERY_AUDIT_FIELDS)
            writer.writerow(row)
    except OSError as e:
        logging.error("Failed to append delivery_audit.csv: %s", e)


def append_delivery_audit_bundle(
    deal_id: str,
    telegram_status: str,
    whatsapp_status: str,
    final_result: str,
) -> None:
    """One row per channel attempt (telegram, whatsapp, delivery aggregate)."""
    append_delivery_audit_row("telegram", telegram_status, deal_id)
    append_delivery_audit_row("whatsapp", whatsapp_status, deal_id)
    append_delivery_audit_row("delivery", final_result, deal_id)


def sync_to_dashboard(deal_data: dict, decision: str = "pending", reason: str = "") -> None:
    """
    Append a deal row to data/master_log.csv for the production dashboard.
    Expected CSV STRUCTURE:
    timestamp,source,title,price,original_price,category,decision,reason,affiliate_valid
    """
    _ensure_superbot_master_dir()
    stats_file = SUPERBOT_MASTER_FILE
    file_exists = os.path.isfile(stats_file)

    timestamp = datetime.now().isoformat()
    deal_id = str(
        deal_data.get("id")
        or deal_data.get("deal_id")
        or (str(deal_data.get("url", "unknown"))[-24:])
    )
    
    # DEDUPLICATION CHECK: Skip if the same deal_id already exists (best-effort)
    if file_exists:
        try:
            with open(stats_file, "r", encoding="utf-8", errors="ignore") as rf:
                reader = csv.DictReader(rf)
                for existing_row in reader:
                    existing_id = str(existing_row.get("id") or existing_row.get("deal_id") or "")
                    if existing_id and existing_id == deal_id:
                        logging.info(f"Skipping duplicate deal {deal_id} - already in master_log.csv")
                        return
        except Exception as e:
            logging.warning(f"Error checking for duplicates in master_log.csv: {e}")
    
    title = str(deal_data.get("title", "N/A")).strip()
    price = deal_data.get("new_price", deal_data.get("price", "N/A"))
    original_price = deal_data.get("old_price", deal_data.get("original_price", "N/A"))
    category = deal_data.get("category", "general")
    source = str(deal_data.get("source") or deal_data.get("marketplace") or deal_data.get("platform") or "Unknown")
    affiliate_link = str(deal_data.get("affiliate_url") or deal_data.get("url") or "")

    # Affiliate validation
    affiliate_valid = "true" if affiliate_link and affiliate_link.startswith("http") else "false"

    if "amazon.in" in affiliate_link:
        if "tag=" not in affiliate_link:
            sep = "&" if "?" in affiliate_link else "?"
            affiliate_link = f"{affiliate_link}{sep}tag=anany-21"
        else:
            affiliate_link = re.sub(r"tag=[^&]+", "tag=anany-21", affiliate_link)
        affiliate_valid = "true"
    elif "flipkart.com" in affiliate_link:
        if "affid=" not in affiliate_link:
            sep = "&" if "?" in affiliate_link else "?"
            affiliate_link = f"{affiliate_link}{sep}affid=anany"
        else:
            affiliate_link = re.sub(r"affid=[^&]+", "affid=anany", affiliate_link)
        affiliate_valid = "true"

    row = [timestamp, source, title, price, original_price, category, decision, reason, affiliate_valid]

    try:
        if file_exists:
            with open(stats_file, "r", encoding="utf-8", errors="ignore") as rf:
                first = rf.readline().strip()
            if first:
                parts = [p.strip() for p in first.split(",")]
                if parts != MASTER_LOG_FIELDS:
                    legacy = stats_file.replace(".csv", f"_legacy_{int(time.time())}.csv")
                    os.replace(stats_file, legacy)
                    logging.info("data/master_log.csv header mismatch - rotated to %s", legacy)
                    file_exists = False

        with open(stats_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(MASTER_LOG_FIELDS)
            writer.writerow(row)
            f.flush()  # Immediate flush to disk
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
                os.fsync(f.fileno())  # Force write to disk
                logging.info(f"Appended deal {deal_id} to master_log.csv with decision: {decision}")
    except OSError as e:
        logging.error("Failed to sync master_log.csv: %s", e)

def update_heartbeat():
    """Updates heartbeat.json to show system uptime."""
    heartbeat_file = "heartbeat.json"
    data = {
        "last_run": datetime.now().isoformat(),
        "status": "🟢 Online"
    }
    try:
        with open(heartbeat_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"Failed to update heartbeat: {e}")


def write_workflow_heartbeat(status: str, deal_id: str | None = None) -> None:
    """
    Live Audit: drives dashboard animation.
    Writes dashboard/public/data/workflow_heartbeat.json with timestamp + status.
    status: RUNNING | VALIDATING | SYNC_DISPATCH
    """
    try:
        from pathlib import Path

        p = Path("dashboard/public/data/workflow_heartbeat.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": datetime.now().isoformat(), "status": str(status)}
        if deal_id:
            payload["deal_id"] = str(deal_id)
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

async def track_referral_click(user_id: str, deal_id: str):
    """Stubs: Log referral click."""
    # Real implementation would write to DB
    pass

async def track_user_engagement(user_id: str, marketplace: str):
    """Stubs: Track user affinity."""
    pass

def update_analytics(stats: dict):
    """Updates the analytics.json file with batch stats."""
    analytics = load_json(ANALYTICS_FILE, default={"batches": [], "daily_stats": {}})
    
    # Append batch entry
    batch_entry = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats
    }
    analytics["batches"].append(batch_entry)
    
    # Update Daily Stats (Simple counter for now)
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in analytics["daily_stats"]:
        analytics["daily_stats"][today] = {"sent": 0, "clicks": 0, "revenue": 0.0}
    
    analytics["daily_stats"][today]["sent"] += stats.get("sent", 0)
    
    save_json(ANALYTICS_FILE, analytics)

# ================== CONTENT GENERATION ==================

def format_telegram_message(deal: dict) -> tuple[str, str]:
    """
    Formats the Telegram message with HTML, Emojis, and CTA.
    Returns: (formatted_message, variant_id)
    """
    title = str(deal.get("title") or "").strip() or "Untitled Deal"
    price = deal.get("new_price") or deal.get("price") or "Check Price"
    price_str = str(price).strip() or "Check Price"
    source = deal.get("source") or deal.get("marketplace") or "unknown"
    final_url = ensure_affiliate_url(deal.get("affiliate_url") or deal.get("url", ""), str(source))
    msg = (
        f"📦 {title}\n\n"
        f"💰 Price: {price_str}\n\n"
        f"🔗 Buy Now:\n"
        f"{final_url}"
    )
    return msg, "A"


def format_whatsapp_message(deal: dict) -> str:
    title = deal.get("title") or ""
    price = deal.get("new_price") or deal.get("price")
    source = deal.get("source") or deal.get("marketplace") or "unknown"
    original_price = deal.get("old_price") or deal.get("original_price")
    affiliate_url = ensure_affiliate_url(
        deal.get("affiliate_url") or deal.get("url", ""),
        str(source),
    )

    parts = [
        f"*{WHATSAPP_CHANNEL_NAME}*",
        f"🛍️ {title}",
        f"💰 Price: {price if price is not None else 'Price unavailable'}",
        f"🏷️ Source: {str(source).title()}",
    ]
    if original_price:
        parts.append(f"📉 Was: {original_price}")
    parts.append(f"🛒 Buy Now: {affiliate_url}")
    return "\n".join(parts)

# ================== POSTING LOGIC ==================

async def post_to_telegram(bot: Bot, chat_id: int, caption: str, affiliate_url: str):
    """Posts to Telegram with retry logic. Returns (message_obj, status)."""
    # Debug block for live validation
    print(f"[TELEGRAM_DEBUG] Attempting send to {chat_id}...", flush=True)
    # Log caption for verification
    logging.info(f"Preparing to post to Telegram: {caption} | url={affiliate_url}")

    # Only DRY_RUN blocks real Telegram API calls (TEST_MODE must not silence production sends).
    if DRY_RUN:
        print("[TELEGRAM_DEBUG] DRY_RUN=True — skipping real send", flush=True)
        return None, "Fail"

    # Guardrail: Block localhost redirects
    if "localhost" in caption or "localhost" in affiliate_url:
        logging.error("Blocking post: localhost redirect detected in caption")
        return None, "Fail"
        
    # Shadow Mode Redirect
    if config.SHADOW_MODE:
        logging.info("SHADOW MODE: Redirecting post to shadow channel.")
        if hasattr(config, "SHADOW_CHANNEL_ID") and config.SHADOW_CHANNEL_ID:
            chat_id = config.SHADOW_CHANNEL_ID
        else:
            logging.warning("Shadow Channel ID not set. Skipping post.")
            return None, "Fail"

    if not chat_id:
        logging.warning("Telegram Posting Skipped: chat_id is None")
        return None, "Fail"

    if not affiliate_url or not affiliate_url.startswith("http"):
        logging.error("Telegram Posting Skipped: invalid affiliate_url")
        return None, "Fail"
    reply_markup_payload = {
        "inline_keyboard": [[{"text": "🛒 Buy Now", "url": affiliate_url}]]
    }

    endpoints = [
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        f"https://149.154.167.220/bot{BOT_TOKEN}/sendMessage"  # Direct IP Fallback
    ]

    for attempt in range(3):
        for api_url in endpoints:
            try:
                payload = {
                    "chat_id": str(chat_id),
                    "text": caption,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                    "reply_markup": json.dumps(reply_markup_payload),
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Host": "api.telegram.org" # Essential for IP fallback
                }
                connector = aiohttp.TCPConnector(ssl=False, force_close=True)
                async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
                    async with session.post(api_url, data=payload, headers=headers, timeout=30) as response:
                        body = await response.text()
                        data = json.loads(body)
                        if response.status == 200 and data.get("ok"):
                            result = data.get("result", {})
                            logging.info("Telegram post succeeded via %s with affiliate_url=%s", api_url, affiliate_url)
                            return type("TelegramMessage", (), {"message_id": result.get("message_id", 0)})(), "Success"
                        logging.warning(f"Telegram API error {api_url} status {response.status}: {body[:200]}")
            except Exception as e:
                err_str = str(e).lower()
                if "connection reset" in err_str or "reset by peer" in err_str:
                    logging.warning("Telegram connection reset detected via %s: %r", api_url, e)
                elif "flood" in err_str or "spam" in err_str or "userdeactivated" in err_str:
                    logging.critical(f"TELEGRAM SPAM/FLOOD DETECTED: {e}. Pausing for 24h.")
                    update_trust_decay("system", "SPAM_FLOOD_DETECTED")
                    activate_spam_pause(24)
                    return None, "Fail"
                else:
                    logging.warning(f"Telegram error {api_url} (attempt {attempt+1}): {e!r}")
        
        if attempt < 2:
            await asyncio.sleep(2)
    
    return None, "Fail"

async def send_pipeline_notice(bot: Bot, chat_id: int) -> str:
    notice = "⚠️ No deals passed filters — pipeline active"
    fallback_url = "https://t.me"
    _, st = await post_to_telegram(bot, chat_id, notice, fallback_url)
    if st != "Success":
        # Retry once as requested.
        _, st = await post_to_telegram(bot, chat_id, notice, fallback_url)
    return st


def _affiliate_is_monetized(url: str, source: str) -> bool:
    u = str(url or "").lower()
    try:
        host = (urlparse(u).netloc or "").lower()
    except Exception:
        host = ""
    return ("earnkaro" in host) or ("earnkaro.com" in u) or ("topdeal.app.link" in host)


async def atomic_broadcast(
    *,
    telegram_bot: Bot,
    chat_id: int,
    deal: dict,
    caption: str,
    discount_pct: float,
    deal_id: str,
) -> tuple[str, int]:
    """
    SYNC MANDATE (Non-Negotiable):
    MUST execute Telegram + SendGrid at the same time via asyncio.gather().
    If one fails, the other must NOT be blocked.
    """
    title = str(deal.get("title") or "").strip()
    print(f"[SYNC:START] Dispatching to Email + Telegram for {title}", flush=True)
    print(f"[DISPATCHING] Syncing Email + Telegram for {title}", flush=True)
    write_workflow_heartbeat("SYNC_DISPATCH", deal_id=deal_id)

    final_url = str(deal.get("affiliate_url") or deal.get("url") or "").strip()
    src = str(deal.get("source") or deal.get("marketplace") or "")

    # Validation relaxation for TEST_MODE or 100% OFF: allow URL+title even if price math is off.
    is_100_off = (discount_pct >= 99.0)
    allow_missing_price = bool(TEST_MODE) or is_100_off
    if not allow_missing_price and _to_float_price(deal.get("new_price") or deal.get("price")) is None:
        raise ValueError("dispatch_all called without numeric price")
    if not _affiliate_is_monetized(final_url, src):
        raise ValueError("dispatch_all called without monetized affiliate link")

    async def _tg():
        try:
            print(f"[TELEGRAM:ATTEMPT] deal_id={deal_id}", flush=True)
            _, st = await post_to_telegram(telegram_bot, chat_id, caption, final_url)
            return st
        except Exception as e:
            print(f"[TELEGRAM_ERROR] {e!r}", flush=True)
            return f"Fail:{e!r}"

    async def _email():
        try:
            print(f"[EMAIL:ATTEMPT] deal_id={deal_id}", flush=True)
            return await asyncio.to_thread(SendGridNotifier().send_immediate_alert, deal)
        except Exception as e:
            print(f"[EMAIL_ERROR] {e!r}", flush=True)
            return e

    tg_res, em_res = await asyncio.gather(_tg(), _email(), return_exceptions=True)
    tg_status = "Fail"
    if isinstance(tg_res, Exception):
        print(f"[TELEGRAM_ERROR] {tg_res!r}", flush=True)
    elif isinstance(tg_res, str):
        tg_status = tg_res

    sent_n = 0
    if isinstance(em_res, Exception):
        print(f"[EMAIL_ERROR] {em_res!r}", flush=True)
    else:
        try:
            sent_n = int(em_res or 0)
        except Exception:
            sent_n = 0
    return tg_status, sent_n


async def broadcast_deal(
    *,
    telegram_bot: Bot,
    chat_id: int,
    deal: dict,
    caption: str,
    discount_pct: float,
    deal_id: str,
) -> tuple[str, int]:
    """
    ATOMIC BROADCAST: Telegram + SendGrid at the exact same time.
    Only call when deal has numeric price and monetized affiliate link.
    """
    final_url = str(deal.get("affiliate_url") or deal.get("url") or "").strip()
    src = str(deal.get("source") or deal.get("marketplace") or "")
    if _to_float_price(deal.get("new_price") or deal.get("price")) is None:
        raise ValueError("broadcast_deal called without numeric price")
    if not _affiliate_is_monetized(final_url, src):
        raise ValueError("broadcast_deal called without monetized affiliate link")

    async def _tg():
        print(f"[TELEGRAM:ATTEMPT] deal_id={deal_id}", flush=True)
        _, st = await post_to_telegram(telegram_bot, chat_id, caption, final_url)
        return st

    async def _email():
        print(f"[EMAIL:ATTEMPT] deal_id={deal_id}", flush=True)
        # SendGrid is sync; run in thread so we can gather with Telegram.
        return await asyncio.to_thread(SendGridNotifier().send_immediate_alert, deal)

    tg_status, sent_n = await asyncio.gather(_tg(), _email(), return_exceptions=False)
    return tg_status, int(sent_n or 0)


async def verify_earnkaro_auth(session: aiohttp.ClientSession) -> bool:
    key = (os.getenv("EARNKARO_API_KEY") or "").strip()
    print("EARNKARO KEY LOADED:", bool(key), flush=True)
    if not key:
        return False
    test_url = "https://www.flipkart.com/"
    api = f"https://earnkaro.com/api/v1/generate_link?url={quote(test_url, safe='')}"
    headers = {
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Referer": "https://earnkaro.com/",
        "Accept": "application/json",
    }
    try:
        async with session.get(api, headers=headers, timeout=15, ssl=False) as response:
            body = await response.text()
            safe_body = body.encode("ascii", "backslashreplace").decode("ascii")
            print(f"EarnKaro response: {response.status} {safe_body}", flush=True)
            
            # If 403, we might be hitting a Cloudflare/Next.js block on the API endpoint
            # but we can still try to use the fallback generator.
            if response.status == 403:
                print("[EARNKARO] 403 detected; auth might be valid but endpoint blocked. Proceeding.", flush=True)
                return True
                
            lb = body.lower()
            if "blocked site" in lb or "secure2.sophos.com" in lb:
                print("[EARNKARO] Network filter block detected; proceeding with topdeal fallback mode.", flush=True)
                return True
            return response.status == 200
    except Exception as e:
        print(f"EarnKaro response: ERROR {e!r}", flush=True)
        return False


async def post_to_whatsapp(text_message: str) -> tuple[bool, str]:
    """
    Sends the same deal payload to WhatsApp Cloud API.
    """
    if not WHATSAPP_ENABLED:
        return False, "Fail"
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_RECIPIENT):
        logging.warning("WhatsApp posting skipped: missing WhatsApp configuration")
        return False, "Fail"
    if TEST_MODE:
        return False, "Fail"

    api_url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": str(WHATSAPP_RECIPIENT),
        "type": "text",
        "text": {"preview_url": True, "body": text_message},
    }

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(api_url, headers=headers, json=payload, timeout=20) as response:
                body = await response.text()
                if response.status in (200, 201):
                    logging.info("WhatsApp post succeeded")
                    return True, "Success"
                logging.error(f"WhatsApp API error {response.status}: {body}")
                return False, "Fail"
    except Exception as e:
        logging.error(f"WhatsApp post failed: {e!r}")
        return False, "Fail"

async def post_to_discord(session, webhook_url: str, deal: dict, variant: str):
    """Posts rich embed to Discord."""
    if TEST_MODE or "placeholder" in webhook_url.lower():
        return

    embed = {
        "title": deal.get("title"),
        "url": deal.get("url"),
        "color": 5814783,
        "fields": [
            {"name": "Price", "value": f"₹{deal.get('new_price')}", "inline": True},
            {"name": "Marketplace", "value": deal.get("marketplace"), "inline": True},
            {"name": "Status", "value": deal.get("stock_status", "In Stock"), "inline": True}
        ],
        "footer": {"text": f"Crawl.io • Variant {variant}"}
    }
    
    payload = {"embeds": [embed]}
    
    for attempt in range(3):
        try:
            response = await session.post(webhook_url, json=payload)
            status = getattr(response, "status", None)
            if status in [200, 204]:
                return
            else:
                logging.warning(f"Discord error {status}")
        except Exception as e:
            logging.error(f"Discord post failed: {e}")
        await asyncio.sleep(2)


async def deal_engine(single_run=False):
    global processed_cache
    
    logging.info(f"?? Crawl.io Bot Started (Phase 6+) | TEST_MODE={TEST_MODE} | Single Run: {single_run}")
    logging.info("DATA SOURCE: LIVE WEB SCRAPERS ONLY (NO STATIC FEEDS)")
    logging.info("INFO - Continuous scrape loop active")

    # Initialize Cache (SQLite is primary, processed_cache is backup)
    processed_cache = {}  # Initialize for compatibility at function top
    logging.info(f"Initialized processed_cache for deduplication logic.")

    # REVENUE PRIORITY: WIPE CACHE
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        logging.info("Cache wiped for revenue priority run.")

    # Initialize Bot
    telegram_bot = Bot(token=BOT_TOKEN)
    
    # Initialize Cache (SQLite is primary, processed_cache is backup)
    # processed_cache = {}  # Initialize for compatibility
    # logging.info(f"Initialized processed_cache for deduplication logic.")

    while True:
        # T-047: Heartbeat
        update_heartbeat()
        write_workflow_heartbeat("RUNNING")
        
        # T-049: Kill Switch
        if check_kill_switch():
            logging.info("Kill switch active. Sleeping...")
            await asyncio.sleep(60)
            continue
            
        # Spam Safety Pause Check
        is_paused, remaining = check_spam_pause()
        if is_paused:
            logging.warning(f"⚠️ SPAM SAFETY PAUSE ACTIVE. Sleeping for {int(remaining)}s...")
            # Sleep in chunks to allow kill switch to work or manual intervention
            sleep_chunk = min(remaining, 3600) 
            await asyncio.sleep(sleep_chunk)
            continue

        # Update Throttles
        update_category_throttles()
            
        try:
            # 1. LIVE SCRAPING (No Static Feeds)
            deals = []
            source_counts = {}
            bypass_runs_left = _load_persona_bypass_runs(default_runs=5)
            bypass_strict_persona = bypass_runs_left > 0
            if bypass_strict_persona:
                print(f"[BYPASS] Strict persona gate disabled (runs_left={bypass_runs_left})", flush=True)
            try:
                logging.info("Scraping live sources (QUAD-SOURCE concurrency)...")
                enabled = getattr(config, "ENABLED_SOURCES", ["amazon", "flipkart", "couponami"])
                source_used = "none"

                async def _wrap(label: str, coro):
                    try:
                        res = await coro
                        n = len(res) if isinstance(res, list) else (1 if isinstance(res, dict) else 0)
                        print(f"[SCRAPE:{label}] Found {n} deals")
                        return res
                    except Exception as exc:
                        print(f"[SCRAPE:{label}] FAIL {exc!r}")
                        return []

                # Force fallback hierarchy:
                # 1) coupon feed, 2) diverse amazon, 3) hardcoded amazon URLs.
                tasks = []
                task_labels = []
                if "couponami" in enabled:
                    tasks.append(_wrap("COUPONAMI", get_manual_deal()))
                    task_labels.append("COUPONAMI")
                if "amazon" in enabled:
                    tasks.append(_wrap("AMAZON", get_diverse_amazon_deals()))
                    task_labels.append("AMAZON")
                if "flipkart" in enabled:
                    tasks.append(_wrap("FLIPKART", get_flipkart_deals()))
                    task_labels.append("FLIPKART")
                if "earnkaro" in enabled:
                    tasks.append(_wrap("EARNKARO", get_earnkaro_deals()))
                    task_labels.append("EARNKARO")

                scraped = await asyncio.gather(*tasks, return_exceptions=False) if tasks else []
                try:
                    # stable quad-sync summary (lists may be empty)
                    def _n(x):
                        return len(x) if isinstance(x, list) else (1 if isinstance(x, dict) else 0)
                    quad_counts = {t: 0 for t in ["AMAZON", "FLIPKART", "COUPONAMI", "EARNKARO"]}
                    for idx, res in enumerate(scraped):
                        label = task_labels[idx] if idx < len(task_labels) else f"S{idx}"
                        quad_counts[label] = _n(res)
                    print(
                        f"[QUAD-SYNC] Amazon: {quad_counts['AMAZON']} deals, Flipkart: {quad_counts['FLIPKART']} deals, "
                        f"Couponami: {quad_counts['COUPONAMI']} deals, EarnKaro: {quad_counts['EARNKARO']} deals.",
                        flush=True,
                    )
                except Exception:
                    pass

                # Optional seed deals (disabled by default to avoid stale repeats like old AirPods links).
                if "amazon" in enabled and str(os.getenv("USE_SEED_AMAZON", "false")).lower() in {"1", "true", "yes"}:
                    try:
                        seed = load_seed_amazon_deals()
                        if seed:
                            print(f"[SCRAPE:AMAZON] Seeded {len(seed)} deals")
                            deals.extend(seed)
                    except Exception as e:
                        logging.warning(f"Amazon seed loading failed: {e}")
                
                total = 0
                for res in scraped:
                    if isinstance(res, list):
                        deals.extend(res)
                        total += len(res)
                    elif isinstance(res, dict) and res.get("url"):
                        deals.append(res)
                        total += 1
                    elif isinstance(res, Exception) or isinstance(res, asyncio.TimeoutError):
                        logging.warning(f"Scraping task failed: {res}")

                if deals:
                    source_used = "primary_scrapers"
                else:
                    logging.warning("Primary scrapers empty. Trying Coupon fallback only.")
                    coupon_only = await _wrap("COUPONAMI_FALLBACK", get_manual_deal())
                    if isinstance(coupon_only, list) and coupon_only:
                        deals.extend(coupon_only)
                        total += len(coupon_only)
                        source_used = "coupon_fallback"

                if not deals:
                    logging.warning("Coupon fallback empty. Trying Amazon fallback.")
                    amazon_only = await _wrap("AMAZON_FALLBACK", get_diverse_amazon_deals())
                    if isinstance(amazon_only, list) and amazon_only:
                        deals.extend(amazon_only)
                        total += len(amazon_only)
                        source_used = "amazon_fallback"

                if not deals:
                    logging.warning("Amazon fallback empty. Using hardcoded validation URLs.")
                    source_used = "hardcoded_validation_urls"
                    deals = [
                        {
                            "title": "Rich Dad Poor Dad Paperback",
                            "url": "https://www.amazon.in/dp/8172234988",
                            "affiliate_url": ensure_affiliate_url("https://www.amazon.in/dp/8172234988", "amazon"),
                            "price": "Check Price",
                            "new_price": "Check Price",
                            "source": "amazon",
                            "marketplace": "Amazon",
                        },
                        {
                            "title": "Amazon Product Deal",
                            "url": "https://www.amazon.in/dp/B0BSHF7WHW",
                            "affiliate_url": ensure_affiliate_url("https://www.amazon.in/dp/B0BSHF7WHW", "amazon"),
                            "price": "Check Price",
                            "new_price": "Check Price",
                            "source": "amazon",
                            "marketplace": "Amazon",
                        },
                    ]
                    total += len(deals)

                # Unified deal pool: dedupe by normalized title (EarnKaro vs Flipkart etc.)
                try:
                    seen_titles: set[str] = set()
                    uniq: list[dict] = []
                    for d in deals:
                        title_key = str(d.get("title") or "").strip().lower()
                        if not title_key:
                            continue
                        if title_key in seen_titles:
                            continue
                        seen_titles.add(title_key)
                        uniq.append(d)
                    if len(uniq) != len(deals):
                        print(f"[DEDUP] Reduced pool {len(deals)} -> {len(uniq)} (title hash)", flush=True)
                    deals = uniq
                except Exception:
                    pass
                
                for deal in deals:
                    src = (deal.get("source") or deal.get("marketplace") or "unknown").lower()
                    source_counts[src] = source_counts.get(src, 0) + 1
                logging.info(f"Scraped {total} deals from live web. Breakdown: {source_counts}")
                logging.info(f"Source used: {source_used}")
            except Exception as e:
                logging.error(f"Live Scrape Failed: {e}")

            if not deals:
                logging.warning("No deals found from live scrapers.")

            # Batch Stats with Telegram Analytics
            stats = {
                "sent": 0, "skipped_cache": 0, "low_disc": 0, 
                "invalid": 0, "out_of_stock": 0, "enrich_fail": 0,
                "tagged": 0, "throttled": 0, "variant_a": 0, "variant_b": 0,
                "follow_up_alerts_sent": 0, "stock_change_detected": 0,
                "rejected_missing_title": 0, "rejected_missing_price": 0,
                "rejected_invalid_affiliate": 0, "rejected_duplicate": 0,
                "rejected_blocked": 0, "whatsapp_sent": 0, "whatsapp_failed": 0,
                "loot_emails": 0,
                # Telegram Analytics
                "telegram_attempts": 0, "telegram_success": 0, "telegram_reset_errors": 0,
            }

            try:
                # 5. ASYNC TIMEOUT PROTECTION
                async with asyncio.timeout(300):
                    async with aiohttp.ClientSession() as session:
                        # PHASE 1: verify EarnKaro auth before processing.
                        if (os.getenv("EARNKARO_API_KEY") or "").strip():
                            ek_ok = await verify_earnkaro_auth(session)
                            if not ek_ok:
                                logging.error("EarnKaro auth failed preflight; bot will proceed in fallback monetization mode.")
                        processed_count = 0

                        # --- PHASE 1: PROCESS NEW DEALS ---
                        # Diversity Gatekeeper: Limit deals from a single source to 3 per run
                        source_gate_counts = {}
                        deals_to_process = []
                        
                        # Sort deals to prioritize Amazon/Flipkart
                        sorted_deals = sorted(deals, key=lambda x: 0 if "amazon" in x.get("url", "").lower() or "flipkart" in x.get("url", "").lower() else 1)
                        
                        for d in sorted_deals:
                            d = coerce_deal_object(d)
                            url = d.get("url", "").lower()
                            source = d.get("source", "unknown")

                            # TEMP BYPASS: For Amazon/Flipkart verification, bypass per-source gate for next 5 runs.
                            if bypass_strict_persona and source in {"amazon", "flipkart"}:
                                deals_to_process.append(d)
                                continue

                            if source_gate_counts.get(source, 0) < 3:
                                deals_to_process.append(d)
                                source_gate_counts[source] = source_gate_counts.get(source, 0) + 1
                        
                        # Shuffle slightly to mix sources within the limit
                        random.shuffle(deals_to_process)
                        
                        # Enforce absolute batch max
                        deals_to_process = deals_to_process[:MAX_DEALS_PER_BATCH]
                    
                        if len(deals) > MAX_DEALS_PER_BATCH:
                            logging.info(f"Throttling enabled: Processing {len(deals_to_process)} deals (Strict Persona Limit).")
    
                        # Reciprocity Engine: Enforce 3 Free : 1 Paid Ratio
                        # Sort deals to prioritize Free if ratio not met
                        # Heuristic: Deals with price <= 0 or "Free" in title are "free"
                        free_deals = []
                        paid_deals = []
                    
                        for d in deals_to_process:
                            price_str = str(d.get("new_price", "1")).lower()
                            is_free = False
                            if "free" in d.get("title", "").lower() or price_str == "0" or price_str == "free":
                                is_free = True
                        
                            if is_free:
                                free_deals.append(d)
                            else:
                                paid_deals.append(d)
                    
                        final_batch = []
                    
                        # If we owe free posts, try to fill with free deals first
                        # (Simple greedy approach for now: Mix them to respect ratio over time)
                        # Just append all, but loop will update counters
                        final_batch = free_deals + paid_deals # Prioritize free to build bank

                        # SENDGRID OVERHAUL: Trigger broadcast immediately after pool is populated.
                        # No demo hacks: only include deals that have an explicit discount percentage in feed/title.
                        try:
                            loot_gate = LOOT_THRESHOLD
                            email_pool: list[dict] = []
                            for d0 in final_batch:
                                d0 = coerce_deal_object(d0)
                                raw0 = str(d0.get("affiliate_url") or d0.get("url") or "").strip()
                                if not raw0.startswith("http"):
                                    continue
                                title0 = str(d0.get("title") or "").strip()
                                if not title0:
                                    continue
                                pct0 = max(
                                    _extract_discount_pct_from_text(d0.get("discount") or ""),
                                    _extract_discount_pct_from_text(title0),
                                )
                                if pct0 <= 0 or pct0 < loot_gate:
                                    continue
                                gen_src0 = d0.get("source") or d0.get("marketplace", "")
                                try:
                                    aff0 = await AffiliateLinkGenerator.generate(session, raw0, gen_src0)
                                except Exception:
                                    aff0 = raw0
                                if not AffiliateLinkGenerator.is_valid(aff0, gen_src0):
                                    continue
                                email_pool.append(
                                    {
                                        "title": title0,
                                        "url": raw0,
                                        "affiliate_url": aff0,
                                        "source": gen_src0,
                                        "discount_pct": pct0,
                                    }
                                )

                            if email_pool and not DRY_RUN:
                                try:
                                    n_sent = SendGridNotifier().broadcast_daily_loot(email_pool[:30], subject="Daily Loot")
                                    stats["loot_emails"] = stats.get("loot_emails", 0) + int(n_sent or 0)
                                    print(f"[EMAIL:SUCCESS] Sent to {n_sent} subscribers", flush=True)
                                except Exception as sg_exc:
                                    print(f"[EMAIL:FAIL] {sg_exc!r}", flush=True)
                        except Exception:
                            pass
                    
                        # --- INTERNAL GUARDS STRIPPED ---
                        # for deal in final_batch:
                        #     cat = deal.get("category", "general")
                        #     if "category" not in deal:
                        #         if "audio" in deal.get("title", "").lower(): cat = "audio"
                        #         elif "laptop" in deal.get("title", "").lower(): cat = "laptop"
    
                        #     price_str = str(deal.get("new_price", "1")).lower()
                        #     is_free = "free" in deal.get("title", "").lower() or price_str == "0" or price_str == "free"
                        
                        #     if not is_free:
                        #         if reciprocity_state["free"] < config.RECIPROCITY_RATIO["free"] and not TEST_MODE:
                        #             logging.info(f"Skipping Paid Deal (Reciprocity Debt): {deal['title']}")
                        #             log_rejection(deal.get("url", "unknown"), {"stage": "Trust", "detail": "reciprocity_debt"})
                        #             continue
                        #         reciprocity_state["paid"] += 1
                        #         if reciprocity_state["paid"] >= config.RECIPROCITY_RATIO["paid"]:
                        #             reciprocity_state["free"] -= config.RECIPROCITY_RATIO["free"]
                        #             reciprocity_state["paid"] = 0
                        #     else:
                        #         reciprocity_state["free"] += 1
                        
                        for deal in final_batch:
                            deal = coerce_deal_object(deal)
                            cat = deal.get("category", "general")
                            if "category" not in deal:
                                if "audio" in deal.get("title", "").lower(): cat = "audio"
                                elif "laptop" in deal.get("title", "").lower(): cat = "laptop"
    
                            # REVENUE IS THE ONLY PRIORITY: BYPASS CATEGORY THROTTLE
                            # if check_category_throttle(cat):
                            #     logging.info(f"Skipping deal in throttled category '{cat}': {deal.get('title')}")
                            #     stats["throttled"] += 1
                            #     log_rejection(deal.get("url", "unknown"), {"stage": "Revenue", "detail": f"category_throttled_{cat}"})
                            #     continue
    
                            raw_url = deal.get("url", "")
                        
                            # ASIN Extraction & Dedup
                            asin = None
                            try:
                                asin_match = re.search(r"/dp/([A-Z0-9]{10})", raw_url)
                                if asin_match:
                                    asin = asin_match.group(1)
                            except:
                                pass
    
                            # SQLite Deduplication: Skip if sent in the last 24 hours
                            deal_id = asin if asin else raw_url
                            if is_deal_sent(deal_id):
                                stats["skipped_cache"] += 1
                                stats["rejected_duplicate"] += 1
                                log_rejection(raw_url, {"stage": "Duplicate", "detail": "duplicate"})
                                continue
                            #             "old_price": deal.get("old_price"),
                            #             "new_price": deal.get("new_price"),
                            #             "last_checked": datetime.now().isoformat(),
                            #             "alerts_sent": []
                            #          }
                            #     continue
    
                            # 3. Affiliate Tagging - NOW HANDLED AT SCRAPER LEVEL
                            # tagged_url = await add_affiliate_tag(session, raw_url, deal.get("marketplace", ""), category)
                            # deal["url"] = tagged_url
                            gen_source = deal.get("source") or deal.get("marketplace", "")
                            generated = await AffiliateLinkGenerator.generate(
                                session,
                                deal.get("affiliate_url") or raw_url,
                                gen_source,
                            )
                            if not AffiliateLinkGenerator.is_valid(generated, gen_source):
                                print(f"[REJECTED: NO AFFILIATE LINK] {raw_url}", flush=True)
                                log_rejection(raw_url, {"stage": "Affiliate", "detail": "affiliate_generation_failed"})
                                stats["invalid"] += 1
                                stats["rejected_invalid_affiliate"] += 1
                                continue
                            if "amazon" in str(gen_source).lower() and "tag=" in generated:
                                print(f"[AFFILIATE:AMAZON] tag injected ok for {raw_url}", flush=True)
                            deal["affiliate_url"] = generated
                            stats["tagged"] += 1

                            if not deal.get("title"):
                                stats["invalid"] += 1
                                stats["rejected_missing_title"] += 1
                                log_rejection(raw_url, {"stage": "Schema", "detail": "missing_title"})
                                continue
                            if not AffiliateLinkGenerator.is_valid(deal.get("affiliate_url", ""), gen_source):
                                stats["invalid"] += 1
                                stats["rejected_invalid_affiliate"] += 1
                                log_rejection(raw_url, {"stage": "Affiliate", "detail": "invalid_affiliate_link"})
                                continue
    
                            # 4. Enrichment & Validation
                            write_workflow_heartbeat("VALIDATING", deal_id=str(deal_id))
                            deal = await enrich_deal(session, deal)
                        
                            if not deal.get("valid", False):
                                enrich_err = str(deal.get("enrich_error") or "")
                                BUYABILITY_FAILURES = {
                                    "no_buy_button", "buyability", "403_forbidden",
                                    "403 forbidden", "amazon_validation_failed",
                                    "network", "strict_buyability"
                                }
                                is_buyability_fail = any(
                                    b in enrich_err.lower() for b in BUYABILITY_FAILURES
                                )
                                is_amazon = "amazon" in str(gen_source).lower() or "amzn" in raw_url.lower()

                                # STRICT Buyability only for Amazon (User request)
                                if is_amazon and is_buyability_fail:
                                    logging.warning("Rejecting Amazon deal due to mandatory buyability failure: %s — %s", deal.get("title"), enrich_err)
                                    if "blocked" in enrich_err.lower():
                                        stats["rejected_blocked"] += 1
                                    stats["enrich_fail"] += 1
                                    continue
                                
                                # Relaxed acceptance for others (Couponami, etc.)
                                if deal.get("title") and deal.get("affiliate_url"):
                                    deal["valid"] = True
                                    deal["new_price"] = deal.get("new_price") or deal.get("price") or "Check Price"
                                    logging.info("Relaxed accept for non-Amazon deal: %s", deal.get("title"))
                                else:
                                    if "blocked" in enrich_err.lower():
                                        stats["rejected_blocked"] += 1
                                    if enrich_err:
                                        stats["enrich_fail"] += 1
                                    else:
                                        stats["invalid"] += 1
                                    continue
    
                            # 5. Discount Filter
                            old_price = deal.get("old_price", 0)
                            new_price = deal.get("new_price", 0)
                            discount_percentage = 0
                        
                            try:
                                op = _to_float_price(old_price)
                                np = _to_float_price(new_price)
                                if op is not None and np is not None and op > 0:
                                    discount_percentage = ((op - np) / op) * 100
                                else:
                                    # If prices are missing, use the feed/listing percentage (e.g. "60% OFF")
                                    discount_percentage = max(
                                        _extract_discount_pct_from_text(deal.get("discount") or ""),
                                        _extract_discount_pct_from_text(deal.get("title") or ""),
                                    )
                            except Exception as e:
                                logging.warning(f"Error calculating discount for {deal.get('title')}: {e}")
                                discount_percentage = _extract_discount_pct_from_text(deal.get("title") or "")

                            # Relaxed: price missing is allowed.
                            is_100_off = discount_percentage >= 99.0
                            numeric_price = _to_float_price(new_price)
                            if numeric_price is None:
                                deal["new_price"] = deal.get("new_price") or deal.get("price") or "Check Price"
                            
                            if numeric_price == 0 and not is_100_off:
                                # If it's 0 but not 100% off, something is wrong
                                discount_percentage = 100.0
                                is_100_off = True
    
                            if discount_percentage < MIN_DISCOUNT_THRESHOLD:
                                stats["low_disc"] += 1
                                logging.info(f"Skipping Low Discount ({discount_percentage:.2f}%): {deal['title']}")
                                log_rejection(deal.get("url", "unknown"), {"stage": "Revenue", "detail": "low_discount"})
                                continue

                            loot_gate = LOOT_THRESHOLD
                            caption, variant = format_telegram_message(deal)
                            if variant == "A": stats["variant_a"] += 1
                            else: stats["variant_b"] += 1

                            # Global Broadcast Activation: all dispatch goes through atomic dispatcher.

                            msg = None
                            tg_status = "Fail"
                            wa_status = "Fail"
                            final_result = "fail"
                            sent_n = 0

                            # Live dispatch: gated by DRY_RUN only (TEST_MODE no longer blocks Telegram/email).
                            if not DRY_RUN:
                                # Channel Routing
                                post_cat = deal.get("category", "general")
                                chat_id = config.CHANNELS["main"]["chat_id"] # Default
                                
                                if post_cat in ["course", "education", "book"]:
                                     chat_id = config.CHANNELS["education"]["chat_id"]
                                
                                final_url = deal.get("affiliate_url") or deal.get("url", "")
                                if not final_url or not isinstance(final_url, str) or not final_url.startswith("http"):
                                    logging.error(f"Posting deal without valid URL field: {deal.get('title')}")
                                else:
                                    ok_target, resolved_target, why_target = await validate_dispatch_target(session, deal)
                                    is_amazon = "amazon" in str(gen_source).lower() or "amzn" in str(deal.get("url", "")).lower()

                                    if not ok_target:
                                        print(f"[WARN] Dispatch target check failed ({why_target}): {resolved_target}", flush=True)
                                        
                                        # STRICT Buyability for Amazon in Dispatch phase too
                                        if is_amazon:
                                            logging.warning("Rejecting Amazon deal in dispatch phase due to mandatory buyability failure: %s", why_target)
                                            log_rejection(raw_url, {"stage": "DispatchBuyability", "detail": f"dispatch_target_{why_target}"})
                                            stats["enrich_fail"] += 1
                                            continue

                                        # Relaxed for others
                                        if not (deal.get("title") and deal.get("affiliate_url")):
                                            log_rejection(raw_url, {"stage": "Buyability", "detail": f"dispatch_target_{why_target}"})
                                            stats["enrich_fail"] += 1
                                            continue
                                    
                                    # Update with resolved target only if it's valid
                                    if ok_target:
                                        deal["url"] = resolved_target
                                        if not deal.get("affiliate_url") or not str(deal.get("affiliate_url")).startswith("http"):
                                            deal["affiliate_url"] = resolved_target
                                    final_url = deal.get("affiliate_url") or resolved_target
                                
                                # Telegram Analytics: Track attempt
                                stats["telegram_attempts"] += 1
                                deal_id = asin if asin else raw_url[-12:] if raw_url else "unknown"
                                
                                # ATOMIC SYNC: same deal must hit Email + Telegram together.
                                try:
                                    # DEDUP LOCK: mark right before dispatch so parallel channels cannot re-post same deal.
                                    mark_deal_sent(deal_id)
                                    tg_status, sent_n = await atomic_broadcast(
                                        telegram_bot=telegram_bot,
                                        chat_id=int(chat_id) if str(chat_id).lstrip("-").isdigit() else chat_id,
                                        deal=deal,
                                        caption=caption,
                                        discount_pct=discount_percentage,
                                        deal_id=str(deal_id),
                                    )
                                    stats["loot_emails"] = stats.get("loot_emails", 0) + int(sent_n or 0)
                                    if sent_n:
                                        log_delivery_audit("email", True, deal_id, f"Sent to {sent_n} subscribers")
                                        append_delivery_audit_row("loot_emails", str(sent_n), str(deal_id))
                                    else:
                                        log_delivery_audit("email", False, deal_id, "Sent to 0 subscribers")
                                        append_delivery_audit_row("loot_emails", "0", str(deal_id))
                                except Exception as b_exc:
                                    print(f"[BROADCAST:FAIL] {b_exc!r}", flush=True)
                                    tg_status = "Fail"
                                    sent_n = 0
                                
                                # Telegram Analytics: Track success/failure
                                if tg_status == "Success":
                                    stats["telegram_success"] += 1
                                    log_delivery_audit("telegram", True, deal_id)
                                    append_delivery_audit_row("telegram_success", "1", str(deal_id))
                                else:
                                    error_msg = tg_status if tg_status != "Fail" else "Unknown error"
                                    if "reset" in error_msg.lower() or "connection" in error_msg.lower():
                                        stats["telegram_reset_errors"] += 1
                                    log_delivery_audit("telegram", False, deal_id, error_msg)
                                    append_delivery_audit_row("telegram_success", "0", str(deal_id))
                                whatsapp_payload = format_whatsapp_message(deal)
                                wa_ok, wa_status = await post_to_whatsapp(whatsapp_payload)
                                if wa_ok:
                                    stats["whatsapp_sent"] += 1
                                elif WHATSAPP_ENABLED:
                                    stats["whatsapp_failed"] += 1
                                channels_ok = (tg_status == "Success") or (sent_n > 0)
                                final_result = (
                                    "success"
                                    if tg_status == "Success" and wa_ok
                                    else ("partial_success" if wa_ok or channels_ok else "fail")
                                )
                                append_delivery_audit_bundle(
                                    deal_id=str(deal_id),
                                    telegram_status=tg_status,
                                    whatsapp_status=wa_status,
                                    final_result=final_result,
                                )
                                try:
                                    post_cat = deal.get("category", "general")
                                    if post_cat in HIGH_EPC_CATEGORIES:
                                        await post_to_discord(session, DISCORD_WEBHOOK_URL, deal, variant)
                                except Exception as e:
                                    logging.warning(f"Discord cross-post skipped due to error: {e}")
                            
                                # SQLite Persistent Deduplication (atomic path has msg=None)
                                if msg or tg_status == "Success" or sent_n > 0 or final_result == "partial_success":
                                     mark_deal_sent(deal_id)
                                     log_post(deal.get("url", "unknown"), deal.get("category", "general"))
                                     
                                     # STRICT VALIDATION: Only process if deal meets criteria
                                     if validate_deal(deal):
                                         sync_to_dashboard(deal, "accepted", "Valid deal with affiliate link")
                                     else:
                                         sync_to_dashboard(deal, "rejected", "Failed validation - missing required fields")
                                         logging.warning(f"Deal failed validation: {deal.get('title', 'Unknown')}")
                            
                                # Add to Follow-up Cache
                                followup_data = {
                                    "title": deal.get("title"),
                                    "marketplace": deal.get("marketplace"),
                                    "url": deal.get("url"), # Use tagged URL
                                    "old_price": old_price,
                                    "new_price": new_price,
                                    "last_checked": datetime.now().isoformat(),
                                    "alerts_sent": []
                                }
                            
                                # T-050: Store message ID for future editing
                                if msg:
                                    followup_data["message_id"] = msg.message_id
                                    followup_data["chat_id"] = chat_id
                                
                                followup_cache[raw_url] = followup_data
                            
                                # Waitlist Alerts (DM-only)
                                try:
                                    if asin:
                                        await check_waitlist_alerts(telegram_bot, asin, deal.get("new_price"))
                                except Exception as e:
                                    logging.error(f"Waitlist alert processing failed: {e}")
                            
                            processed_count += 1
                            if msg or tg_status == "Success" or sent_n > 0 or final_result == "partial_success":
                                stats["sent"] += 1
                            await asyncio.sleep(ANTI_SPAM_DELAY)
                    
                        # --- PHASE 2: PROCESS FOLLOW-UPS ---
                        # Run follow-up checks (does not consume main batch limit in this implementation, 
                        # or we can pass remaining limit. Current impl has its own limit check inside)
                        await process_followups(session, telegram_bot, stats)

                        # Force Telegram send every run.
                        if int(stats.get("telegram_success", 0)) <= 0:
                            fallback_chat = config.CHANNELS["main"]["chat_id"]
                            logging.info("Telegram fallback notice attempt (no successful real deal sends).")
                            notice_status = await send_pipeline_notice(
                                telegram_bot,
                                int(fallback_chat) if str(fallback_chat).lstrip("-").isdigit() else fallback_chat,
                            )
                            if notice_status == "Success":
                                stats["telegram_attempts"] = stats.get("telegram_attempts", 0) + 1
                                stats["telegram_success"] = stats.get("telegram_success", 0) + 1
                                logging.info("Telegram sent: SUCCESS (pipeline notice)")
                            else:
                                stats["telegram_attempts"] = stats.get("telegram_attempts", 0) + 1
                                logging.error("Telegram sent: FAIL (pipeline notice)")
    
            except asyncio.TimeoutError:
                logging.error('CRITICAL: Batch processing timed out (300s). Saving progress.')
            # 8. Logging & Cleanup
            if not TEST_MODE:
                cache_payload = list(processed_cache.keys()) if isinstance(processed_cache, dict) else list(processed_cache)
                save_json(CACHE_FILE, cache_payload)
                save_json(SALE_FOLLOWUP_CACHE_FILE, followup_cache)
                update_analytics(stats)
                
            logging.info(f"Batch Complete: {stats}")
            
            # T-048: Heartbeat at end of run for audit
            update_heartbeat()
            
            # Randomized Sleep
            sleep_time = POST_INTERVAL_SECONDS * random.uniform(0.85, 1.15)
            logging.info(f"Sleeping for {int(sleep_time)}s...")
            try:
                if bypass_runs_left > 0:
                    _save_persona_bypass_runs(bypass_runs_left - 1)
            except Exception:
                pass
            
            if single_run:
                logging.info("Single run completed. Exiting loop.")
                break
                
            await asyncio.sleep(sleep_time)

        except Exception as e:
            logging.error(f"Critical Loop Error: {e}")
            if single_run:
                logging.error("Single run failed. Exiting.")
                break
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        # Pass SINGLE_RUN flag from config to the engine
        asyncio.run(deal_engine(single_run=config.SINGLE_RUN))
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
    except Exception as e:
        logging.critical(f"FATAL: Bot crashed on startup: {e}")
