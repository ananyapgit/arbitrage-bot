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
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote

import aiohttp
from cachetools import TTLCache
from telegram import Bot
from telegram.error import TelegramError

from scrapers.manual_feed import get_manual_deal
from scrapers.courses import get_free_courses
from scrapers.amazon import get_amazon_product, get_diverse_amazon_deals
from scrapers.flipkart import get_flipkart_product
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
LOOT_THRESHOLD = 1.0 # EMAIL TEST TRIGGER: 1% (was 50%)
FORCE_EMAIL_TEST = True # FORCE EMAIL TESTING: True
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


def normalize_price(value):
    if value is None:
        return None
    cleaned = str(value).replace("₹", "").replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    return cleaned


def ensure_affiliate_url(url: str, source: str) -> str:
    if not url:
        return ""

    parsed = urlparse(url)
    params = dict(parse_qs(parsed.query, keep_blank_values=True))
    source_l = (source or "").lower()

    if "amazon" in source_l or "amazon." in parsed.netloc:
        params["tag"] = [config.AFFILIATE_TAGS.get("amazon.in") or "anany-21"]
    elif "flipkart" in source_l or "flipkart" in parsed.netloc:
        params["affid"] = [config.AFFILIATE_TAGS.get("flipkart.com") or "anany"]

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
    STRICT DATA VALIDATION: A deal MUST have:
    1. A specific title (not category-style)
    2. A specific price (not a range)
    3. discount_percentage > 20%
    
    Returns False if any validation fails.
    """
    # Rule 1: Specific title validation
    title = deal_data.get("title", "")
    if not title or len(title) < 3:
        return False
    
    # Reject category-style titles
    title_lower = title.lower()
    category_keywords = ["sale", "off", "deal", "offer", "discount", "electronics", "fashion", "accessories", "best", "top", "popular", "today's", "deals of the day"]
    if any(keyword in title_lower for keyword in category_keywords):
        return False
    
    # Rule 2: Specific price validation (not a range)
    price = deal_data.get("new_price") or deal_data.get("price")
    if not price:
        return False
    
    # Convert price to float for validation
    try:
        price_str = str(price).replace("?", "").replace("$", "").replace(",", "").strip()
        price_val = float(price_str)
        
        # Reject if price is a range indicator or invalid
        if "-" in price_str or "to" in price_str.lower() or "up to" in price_str.lower():
            return False
        
        # Reject if price is unrealistic
        if price_val < 1 or price_val > 50000:
            return False
            
    except (ValueError, TypeError):
        return False
    
    # Rule 3: Discount percentage > 20%
    discount_pct = deal_data.get("discount_percentage") or deal_data.get("discount_percent")
    if not discount_pct:
        return False
    
    try:
        discount_val = float(str(discount_pct).replace("%", ""))
        if discount_val <= 20.0:
            return False
    except (ValueError, TypeError):
        return False
    
    # All validations passed
    return True

def log_delivery_audit(attempt_type: str, success: bool, deal_id: str, error_msg: str = ""):
    """
    Logs delivery attempts to delivery_audit.csv for dashboard tracking.
    Tracks Telegram uptime and success rates.
    """
    import csv
    from datetime import datetime
    
    audit_file = "dashboard/public/data/delivery_audit.csv"
    os.makedirs(os.path.dirname(audit_file), exist_ok=True)
    
    file_exists = os.path.isfile(audit_file)
    
    try:
        with open(audit_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "attempt_type", "success", "deal_id", "error_message"])
            
            writer.writerow([
                datetime.now().isoformat(),
                attempt_type,
                "success" if success else "failed",
                deal_id,
                error_msg
            ])
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
    conn = sqlite3.connect("sent_deals.db")
    c = conn.cursor()
    # Check if deal was sent in the last 24 hours
    limit = (datetime.now() - timedelta(hours=24)).isoformat()
    c.execute("SELECT 1 FROM sent_deals WHERE product_id=? AND timestamp > ?", (product_id, limit))
    res = c.fetchone()
    conn.close()
    return res is not None

def mark_deal_sent(product_id):
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

    # SPECIALIZED SCRAPERS
    if "amazon" in url or "amzn" in url:
        logging.info(f"Invoking Amazon Scraper for: {url}")
        try:
            amz_data = await get_amazon_product(url)
            if amz_data:
                deal.update(amz_data)
                # Ensure price fields match schema
                if "price" in amz_data:
                     deal["new_price"] = amz_data["price"]
                
                # FAIL-SAFE: If scraper returned empty price or title, set defaults
                if not deal.get("title") or deal.get("title") == "N/A":
                    deal["title"] = "Limited Time Offer"
                if not deal.get("new_price") or deal.get("new_price") == "N/A":
                    deal["new_price"] = "Check Best Price"
                    
                deal["valid"] = True
                return deal
            else:
                # FAIL-SAFE ENRICHMENT: Even if scraper returns None, we MUST post if we have a URL
                logging.warning(f"Amazon Scraper returned None for {url}. Using defaults.")
                deal.update({
                    "title": "Limited Time Offer",
                    "new_price": "Check Best Price",
                    "valid": True
                })
                return deal
        except Exception as e:
            logging.error(f"Amazon Scraper Exception: {e}")
            # FAIL-SAFE ENRICHMENT: Continue even on exception
            deal.update({
                "title": "Limited Time Offer",
                "new_price": "Check Best Price",
                "valid": True,
                "enrich_error": f"Exception: {e}"
            })
            return deal

    # SPECIALIZED SCRAPERS: Flipkart
    if "flipkart.com" in url:
        logging.info(f"Invoking Flipkart Scraper for: {url}")
        try:
            fk_data = await get_flipkart_product(url)
            if fk_data:
                deal.update(fk_data)
                if "price" in fk_data:
                     deal["new_price"] = fk_data["price"]
                
                # FAIL-SAFE: If scraper returned empty price or title, set defaults
                if not deal.get("title") or deal.get("title") == "N/A":
                    deal["title"] = "Limited Time Offer"
                if not deal.get("new_price") or deal.get("new_price") == "N/A":
                    deal["new_price"] = "Check Best Price"
                    
                deal["valid"] = True
                return deal
            else:
                logging.warning(f"Flipkart Scraper returned None for {url}. Using defaults.")
                deal.update({"title": "Limited Time Offer", "new_price": "Check Best Price", "valid": True})
                return deal
        except Exception as e:
            logging.error(f"Flipkart Scraper Exception: {e}")
            deal.update({"title": "Limited Time Offer", "new_price": "Check Best Price", "valid": True, "enrich_error": f"Exception: {e}"})
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

                # LEVEL 4: Buyability Failures - MODIFIED FOR REVENUE PRIORITY
                # Strict buyability check is removed. If a URL is found, it is considered buyable.
                buy_markers = ["add to cart", "buy now", "proceed to buy"]
                has_buy_button = any(x in text_lower for x in buy_markers)

                if has_buy_button:
                    deal["valid"] = True  # If a buy button is found, the deal is valid.

                # Fallback for messy or missing title/price
                if not deal.get("title") or not str(deal.get("title")).strip():
                    deal["title"] = '🔥 MEGA DEAL'
                
                price = deal.get("new_price")
                try:
                    # A simple check to see if price is a reasonable number
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
    "id",
    "title",
    "price",
    "original_price",
    "discount",
    "category",
    "platform",
    "affiliate_link",
]
DELIVERY_AUDIT_FIELDS = ["timestamp", "channel", "status", "deal_id"]


def _ensure_dashboard_dir() -> str:
    stats_dir = "dashboard/public/data"
    os.makedirs(stats_dir, exist_ok=True)
    return stats_dir


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


def sync_to_dashboard(deal_data: dict) -> None:
    """
    Append a deal row to dashboard/public/data/master_log.csv with deduplication.
    Schema: timestamp, id, title, price, original_price, discount, category, platform, affiliate_link
    NEVER OVERWRITES - Always APPENDS and DEDUPLICATES.
    """
    stats_dir = _ensure_dashboard_dir()
    stats_file = os.path.join(stats_dir, "master_log.csv")
    file_exists = os.path.isfile(stats_file)

    timestamp = datetime.now().isoformat()
    deal_id = (
        deal_data.get("id")
        or deal_data.get("deal_id")
        or (str(deal_data.get("url", "unknown"))[-24:])
    )
    
    # DEDUPLICATION CHECK: Skip if deal ID already exists in CSV
    if file_exists:
        try:
            with open(stats_file, "r", encoding="utf-8", errors="ignore") as rf:
                reader = csv.DictReader(rf)
                for existing_row in reader:
                    existing_id = existing_row.get('id') or existing_row.get('deal_id')
                    if existing_id == deal_id:
                        logging.info(f"Skipping duplicate deal {deal_id} - already in master_log.csv")
                        return
        except Exception as e:
            logging.warning(f"Error checking for duplicates in master_log.csv: {e}")
    
    title = str(deal_data.get("title", "N/A")).strip()
    price = deal_data.get("new_price", deal_data.get("price", "N/A"))
    original_price = deal_data.get("old_price", deal_data.get("original_price", "N/A"))
    category = deal_data.get("category", "general")
    platform = str(deal_data.get("marketplace") or deal_data.get("platform") or deal_data.get("source") or "Unknown")
    affiliate_link = str(deal_data.get("affiliate_url") or deal_data.get("url") or "")

    if "amazon.in" in affiliate_link:
        if "tag=" not in affiliate_link:
            sep = "&" if "?" in affiliate_link else "?"
            affiliate_link = f"{affiliate_link}{sep}tag=anany-21"
        else:
            affiliate_link = re.sub(r"tag=[^&]+", "tag=anany-21", affiliate_link)
    elif "flipkart.com" in affiliate_link:
        if "affid=" not in affiliate_link:
            sep = "&" if "?" in affiliate_link else "?"
            affiliate_link = f"{affiliate_link}{sep}affid=anany"
        else:
            affiliate_link = re.sub(r"affid=[^&]+", "affid=anany", affiliate_link)

    discount_pct = 0.0
    try:
        op = float(str(original_price).replace(",", "").replace("₹", "").strip() or 0)
        np = float(str(price).replace(",", "").replace("₹", "").strip() or 0)
        if op > np and op > 0:
            discount_pct = round(((op - np) / op) * 100, 2)
    except (TypeError, ValueError):
        pass
    discount_str = f"{discount_pct:.2f}" if discount_pct else ""

    row = [
        timestamp,
        deal_id,
        title,
        price,
        original_price,
        discount_str,
        category,
        platform,
        affiliate_link,
    ]

    try:
        if file_exists:
            with open(stats_file, "r", encoding="utf-8", errors="ignore") as rf:
                first = rf.readline().strip()
            if first:
                parts = [p.strip() for p in first.split(",")]
                if parts != MASTER_LOG_FIELDS:
                    legacy = stats_file.replace(".csv", f"_legacy_{int(time.time())}.csv")
                    os.replace(stats_file, legacy)
                    logging.info("master_log.csv header mismatch — rotated to %s", legacy)
                    file_exists = False

        with open(stats_file, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(MASTER_LOG_FIELDS)
                writer.writerow(row)
                f.flush()  # Immediate flush to disk
                os.fsync(f.fileno())  # Force write to disk
                logging.info(f"Appended deal {deal_id} to master_log.csv")
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
    title = deal.get("title", "Limited Time Offer")
    price = deal.get("new_price") or deal.get("price") or "Check Best Price"
    source = deal.get("source") or deal.get("marketplace") or "unknown"
    original_price = deal.get("old_price") or deal.get("original_price")
    
    # Currency formatting
    def format_currency(val):
        s = str(val)
        if s.replace('.','',1).isdigit():
            return f"₹{s}"
        return s

    price_str = format_currency(price)
    
    # REVENUE-FIRST TAGGING: Every link must be tagged.
    # deal["url"] should already have anany-21 from scrapers or add_affiliate_tag
    final_url = ensure_affiliate_url(deal.get("affiliate_url") or deal.get("url", ""), str(source))

    lines = [
        f"🛍️ <b>{title}</b>",
        f"💰 Price: <b>{price_str}</b>",
        f"🏷️ Source: <b>{str(source).title()}</b>",
    ]
    if original_price:
        lines.append(f"📉 Was: <b>{format_currency(original_price)}</b>")
    discount = deal.get("discount_percentage") or deal.get("discount_percent")
    if discount:
        lines.append(f"🔥 Discount: <b>{discount}%</b>")
    msg = "\n".join(lines)
    
    return msg, "A"


def format_whatsapp_message(deal: dict) -> str:
    title = deal.get("title", "Limited Time Offer")
    price = deal.get("new_price") or deal.get("price") or "Check Best Price"
    source = deal.get("source") or deal.get("marketplace") or "unknown"
    original_price = deal.get("old_price") or deal.get("original_price")
    affiliate_url = ensure_affiliate_url(
        deal.get("affiliate_url") or deal.get("url", ""),
        str(source),
    )

    parts = [
        f"*{WHATSAPP_CHANNEL_NAME}*",
        f"🛍️ {title}",
        f"💰 Price: {price}",
        f"🏷️ Source: {str(source).title()}",
    ]
    if original_price:
        parts.append(f"📉 Was: {original_price}")
    parts.append(f"🛒 Buy Now: {affiliate_url}")
    return "\n".join(parts)

# ================== POSTING LOGIC ==================

async def post_to_telegram(bot: Bot, chat_id: int, caption: str, affiliate_url: str):
    """Posts to Telegram with retry logic. Returns (message_obj, status)."""
    # Log caption for verification
    logging.info(f"Preparing to post to Telegram: {caption} | url={affiliate_url}")

    if TEST_MODE:
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

    for attempt in range(3):
        try:
            payload = {
                "chat_id": str(chat_id),
                "text": caption,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
                "reply_markup": json.dumps(reply_markup_payload),
            }
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                async with session.post(api_url, data=payload, timeout=20) as response:
                    data = await response.json(content_type=None)
                    if response.status == 200 and data.get("ok"):
                        result = data.get("result", {})
                        logging.info("Telegram post succeeded with affiliate_url=%s", affiliate_url)
                        return type("TelegramMessage", (), {"message_id": result.get("message_id", 0)})(), "Success"
                    raise TelegramError(f"Bot API error {response.status}: {data}")
        except asyncio.TimeoutError as e:
            if attempt == 2:
                logging.error(f"Telegram timeout (final): {e!r}")
                update_trust_decay("system", f"TELEGRAM_TIMEOUT_FINAL: {e}")
                return None, "Timeout"
            logging.warning(f"Telegram timeout (attempt {attempt+1}): {e!r}")
            await asyncio.sleep(2)
        except Exception as e:
            err_str = str(e).lower()
            if "flood" in err_str or "spam" in err_str or "userdeactivated" in err_str:
                logging.critical(f"TELEGRAM SPAM/FLOOD DETECTED: {e}. Pausing for 24h.")
                update_trust_decay("system", "SPAM_FLOOD_DETECTED")
                # Activate 24h Safety Pause
                activate_spam_pause(24)
                await asyncio.sleep(60) # Short sleep before loop catches the pause
                return None, "Fail"
            
            if attempt == 2:
                logging.error(f"Telegram error (final): {e!r}")
                update_trust_decay("system", f"TELEGRAM_ERROR_FINAL: {e}")
            else:
                logging.warning(f"Telegram error (attempt {attempt+1}): {e!r}")
                await asyncio.sleep(2)
    return None, "Fail"


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
            try:
                logging.info("Scraping live sources...")
                tasks = []
                
                enabled = getattr(config, "ENABLED_SOURCES", ['amazon', 'flipkart', 'couponami'])
                
                if 'couponami' in enabled:
                    try:
                        tasks.append(get_manual_deal())
                    except Exception:
                        pass
                
                if 'amazon' in enabled:
                    try:
                        tasks.append(get_diverse_amazon_deals())
                    except Exception:
                        pass
                    try:
                        deals.extend(load_seed_amazon_deals())
                    except Exception as e:
                        logging.warning(f"Amazon seed loading failed: {e}")
                
                # PARALLEL SCRAPE RECOVERY: Handle timeouts properly
                if tasks:
                    try:
                        # Set individual timeouts for each scraper
                        timeout_tasks = [asyncio.wait_for(task, timeout=30.0) for task in tasks]
                        scraped = await asyncio.gather(*timeout_tasks, return_exceptions=True)
                    except asyncio.TimeoutError:
                        logging.warning("Parallel scraping timeout - some sources may be blocked")
                        scraped = []
                    except Exception as e:
                        logging.error(f"Parallel scraping failed: {e}")
                        scraped = []
                else:
                    scraped = []
                
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
                
                for deal in deals:
                    src = (deal.get("source") or deal.get("marketplace") or "unknown").lower()
                    source_counts[src] = source_counts.get(src, 0) + 1
                logging.info(f"Scraped {total} deals from live web. Breakdown: {source_counts}")
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
                            deal["affiliate_url"] = ensure_affiliate_url(
                                deal.get("affiliate_url") or raw_url,
                                deal.get("source") or deal.get("marketplace", ""),
                            )
                            stats["tagged"] += 1

                            if not deal.get("title"):
                                stats["invalid"] += 1
                                stats["rejected_missing_title"] += 1
                                log_rejection(raw_url, {"stage": "Schema", "detail": "missing_title"})
                                continue
                            if not deal.get("price") and not deal.get("new_price"):
                                stats["invalid"] += 1
                                stats["rejected_missing_price"] += 1
                                log_rejection(raw_url, {"stage": "Schema", "detail": "missing_price"})
                                continue
                            if not has_valid_affiliate_url(deal.get("affiliate_url", ""), deal.get("source", "")):
                                stats["invalid"] += 1
                                stats["rejected_invalid_affiliate"] += 1
                                log_rejection(raw_url, {"stage": "Affiliate", "detail": "invalid_affiliate_link"})
                                continue
    
                            # 4. Enrichment & Validation
                            deal = await enrich_deal(session, deal)
                        
                            if not deal.get("valid", False):
                                if "blocked" in str(deal.get("enrich_error", "")).lower():
                                    stats["rejected_blocked"] += 1
                                if "enrich_error" in deal:
                                    stats["enrich_fail"] += 1
                                else:
                                    stats["invalid"] += 1
                                continue
                            
                            if not deal.get("in_stock", True): # Default True if check fails but page valid
                                stats["out_of_stock"] += 1
                                logging.info(f"Skipping OutOfStock: {deal['title']}")
                                log_rejection(deal.get("url", "unknown"), {"stage": "Buyability", "detail": "out_of_stock"})
                                continue
    
                            # 5. Discount Filter
                            old_price = deal.get("old_price", 0)
                            new_price = deal.get("new_price", 0)
                            discount_percentage = 0
                        
                            try:
                                if old_price and new_price is not None:
                                    op = float(str(old_price).replace(",", ""))
                                    np = float(str(new_price).replace(",", ""))
                                    if op > 0:
                                        discount_percentage = ((op - np) / op) * 100
                            except Exception as e:
                                logging.warning(f"Error calculating discount for {deal.get('title')}: {e}")
    
                            if discount_percentage < MIN_DISCOUNT_THRESHOLD:
                                stats["low_disc"] += 1
                                logging.info(f"Skipping Low Discount ({discount_percentage:.2f}%): {deal['title']}")
                                log_rejection(deal.get("url", "unknown"), {"stage": "Revenue", "detail": "low_discount"})
                                continue

                            if discount_percentage > LOOT_THRESHOLD and (not TEST_MODE or FORCE_EMAIL_TEST) and not DRY_RUN:
                                try:
                                    print(f"[EMAIL] Attempting to send deal {deal_id} to subscribers")
                                    loot_n = SendGridNotifier().broadcast_loot_deal(deal, discount_percentage)
                                    stats["loot_emails"] = stats.get("loot_emails", 0) + int(loot_n or 0)
                                    print(f"[EMAIL] Successfully sent deal {deal_id} to {loot_n} recipients")
                                    log_delivery_audit("email", True, deal_id, f"Sent to {loot_n} subscribers")
                                except Exception as sg_err:
                                    logging.warning("Loot email broadcast skipped: %s", sg_err)
                                    print(f"[EMAIL] Failed to send deal {deal_id}: {sg_err}")
                                    log_delivery_audit("email", False, deal_id, str(sg_err))

                            caption, variant = format_telegram_message(deal)
                            if variant == "A": stats["variant_a"] += 1
                            else: stats["variant_b"] += 1

                            msg = None
                            tg_status = "Fail"
                            wa_status = "Fail"
                            final_result = "fail"
    
                            if not TEST_MODE:
                                # Channel Routing
                                post_cat = deal.get("category", "general")
                                chat_id = config.CHANNELS["main"]["chat_id"] # Default
                                
                                if post_cat in ["course", "education", "book"]:
                                     chat_id = config.CHANNELS["education"]["chat_id"]
                                
                                final_url = deal.get("affiliate_url") or deal.get("url", "")
                                if not final_url or not isinstance(final_url, str) or not final_url.startswith("http"):
                                    logging.error(f"Posting deal without valid URL field: {deal.get('title')}")
                                
                                # Telegram Analytics: Track attempt
                                stats["telegram_attempts"] += 1
                                deal_id = asin if asin else raw_url[-12:] if raw_url else "unknown"
                                
                                msg, tg_status = await post_to_telegram(telegram_bot, chat_id, caption, final_url)
                                
                                # Telegram Analytics: Track success/failure
                                if tg_status == "Success":
                                    stats["telegram_success"] += 1
                                    log_delivery_audit("telegram", True, deal_id)
                                else:
                                    error_msg = tg_status if tg_status != "Fail" else "Unknown error"
                                    if "reset" in error_msg.lower() or "connection" in error_msg.lower():
                                        stats["telegram_reset_errors"] += 1
                                    log_delivery_audit("telegram", False, deal_id, error_msg)
                                whatsapp_payload = format_whatsapp_message(deal)
                                wa_ok, wa_status = await post_to_whatsapp(whatsapp_payload)
                                if wa_ok:
                                    stats["whatsapp_sent"] += 1
                                elif WHATSAPP_ENABLED:
                                    stats["whatsapp_failed"] += 1
                                final_result = (
                                    "success"
                                    if tg_status == "Success" and wa_ok
                                    else ("partial_success" if wa_ok else "fail")
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
                            
                                # SQLite Persistent Deduplication
                                if msg or final_result == "partial_success":
                                     mark_deal_sent(deal_id)
                                     log_post(deal.get("url", "unknown"), deal.get("category", "general"))
                                     
                                     # STRICT VALIDATION: Only process if deal meets criteria
                                     if validate_deal(deal):
                                         sync_to_dashboard(deal)
                                     else:
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
                            if msg or final_result == "partial_success":
                                stats["sent"] += 1
                            await asyncio.sleep(ANTI_SPAM_DELAY)
                    
                        # --- PHASE 2: PROCESS FOLLOW-UPS ---
                        # Run follow-up checks (does not consume main batch limit in this implementation, 
                        # or we can pass remaining limit. Current impl has its own limit check inside)
                        await process_followups(session, telegram_bot, stats)

                        # Empty-run acknowledgements intentionally disabled.
    
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
        asyncio.run(deal_engine())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
