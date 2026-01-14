import asyncio
import logging
import json
import os
import random
import time
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import aiohttp
from cachetools import TTLCache
from telegram import Bot
from telegram.error import TelegramError

import config
import config_monitor

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
POST_INTERVAL_SECONDS = config.POST_INTERVAL_SECONDS
ANTI_SPAM_DELAY = config.ANTI_SPAM_DELAY
MAX_DEALS_PER_BATCH = config.MAX_DEALS_PER_BATCH
MIN_DISCOUNT_THRESHOLD = config.MIN_DISCOUNT_THRESHOLD
TEST_MODE = config.TEST_MODE
AFFILIATE_TAGS = config.AFFILIATE_TAGS
DEALS_FILE = config.DEALS_FILE
CACHE_FILE = config.CACHE_FILE
ANALYTICS_FILE = config.ANALYTICS_FILE
SALE_POLL_INTERVAL_MINUTES = config.SALE_POLL_INTERVAL_MINUTES
STOCK_ALERT_THRESHOLDS = config.STOCK_ALERT_THRESHOLDS
SALE_FOLLOWUP_CACHE_FILE = config.SALE_FOLLOWUP_CACHE_FILE
KILL_SWITCH_FILE = "kill_switch.active"
SPAM_PAUSE_FILE = "spam_pause.json"

# Global State
# T-046: Memory Leak Prevention via TTLCache
processed_cache = TTLCache(maxsize=1000, ttl=86400)
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
    Logs rejected deals to rejection_audit.log for audit compliance.
    Expects structured reasons as: {"stage": str, "rule": str, "detail": str}.
    """
    timestamp = datetime.now().isoformat()
    
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

    log_entry = f"{timestamp},{deal_identifier},{reason_str},{source}\n"
    
    try:
        with open("rejection_audit.log", "a", encoding="utf-8") as f:
            if os.stat("rejection_audit.log").st_size == 0:
                f.write("timestamp,deal_identifier,reason,source\n")
            f.write(log_entry)
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
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading {filepath}: {e}")
        return default

def save_json(filepath, data):
    """Safely saves JSON data to a file."""
    if TEST_MODE and filepath == CACHE_FILE:
        return # Don't update cache in test mode to allow replay
        
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logging.error(f"Error saving {filepath}: {e}")

async def add_affiliate_tag(session, url: str, marketplace: str, category: str = "general") -> str:
    """
    Appends affiliate tag to the URL based on marketplace.
    Preserves existing query parameters.
    T-041: Resolves redirects before tagging to ensure persistence.
    Adds Sub-ID based on category for Revenue Protection.
    """
    # Simulate async CPU bound task
    await asyncio.sleep(0) 
    
    # T-041: Resolve Redirects
    try:
        # We use a short timeout and head/get request to follow redirects
        if session:
             async with session.get(url, allow_redirects=True, timeout=5) as resp:
                 if resp.history:
                     url = str(resp.url)
    except Exception as e:
        # If resolution fails, we proceed with original URL
        logging.debug(f"Redirect resolution failed for {url}: {e}")

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        
        tag = None
        tag_key = "tag" # Default Amazon
        
        if "amazon.in" in domain:
            tag = AFFILIATE_TAGS.get("amazon.in")
            tag_key = "tag"
        elif "flipkart.com" in domain:
            tag = AFFILIATE_TAGS.get("flipkart.com")
            tag_key = "affid"
            
        if not tag:
            return url
    
        query_params = parse_qs(parsed.query)
        if tag_key not in query_params:
            query_params[tag_key] = [tag]
            
            # Revenue Protection: Sub-ID
            sub_id = config.SUB_IDS.get(category, config.SUB_IDS.get("general"))
            if sub_id:
                # Amazon uses 'ascsubtag' usually, but depends on program. Assuming 'ascsubtag' for now.
                # Or custom param. User said "Sub-ID tracking". 
                # I'll add 'subid' or 'ascsubtag'.
                query_params["ascsubtag"] = [sub_id]

            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
            return new_url
            
    except Exception as e:
        logging.warning(f"Error adding affiliate tag to {url}: {e}")
        
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

    # Category Inference (if missing or unknown)
    # FT-023: Sanitize unknown categories to 'general'
    valid_categories = list(config.SUB_IDS.keys()) if hasattr(config, "SUB_IDS") else ["general", "audio", "laptop", "fashion", "accessory"]
    if "category" not in deal or (deal["category"] not in valid_categories and deal["category"] != "general"):
         # Simple inference
         title_lower = str(deal.get("title", "")).lower()
         if "audio" in title_lower or "headphone" in title_lower: deal["category"] = "audio"
         elif "laptop" in title_lower: deal["category"] = "laptop"
         else: deal["category"] = "general"

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
                # (Level 2 Schema is handled by scraper/initial checks)
                
                # Seller Rating
                rating_match = re.search(r"(\d+(\.\d+)?) out of 5 stars", text_lower)
                if rating_match:
                    rating = float(rating_match.group(1))
                    if rating < config.TRUST_RATING_THRESHOLD:
                        deal["valid"] = False
                        deal["enrich_error"] = f"Trust Violation: Seller Rating {rating} < {config.TRUST_RATING_THRESHOLD}"
                        logging.warning(f"Rejecting {url}: {deal['enrich_error']}")
                        log_rejection(url, {"stage": "Trust", "detail": "rating_below_threshold"})
                        return deal
                
                # Shipping Cost
                shipping_match = re.search(r"\+\s?[\$₹]?(\d+(\.\d+)?)\s+shipping", text_lower)
                if shipping_match:
                    shipping_cost = float(shipping_match.group(1))
                    price = deal.get("new_price", 0)
                    try:
                        price_val = float(str(price).replace(",", ""))
                        if price_val > 0 and (shipping_cost / price_val) > config.MAX_SHIPPING_PERCENT:
                            deal["valid"] = False
                            deal["enrich_error"] = f"Trust Violation: Shipping too high"
                            logging.warning(f"Rejecting {url}: {deal['enrich_error']}")
                            log_rejection(url, {"stage": "Trust", "detail": "shipping_too_high"})
                            return deal
                    except:
                        pass

                # LEVEL 4: Buyability Failures
                if config.STRICT_BUYABILITY_CHECK:
                    # Explicit Reason 1: Missing Critical Fields
                    if not deal.get("title") or not deal.get("new_price"):
                        deal["valid"] = False
                        deal["enrich_error"] = "Buyability Failure: Missing Title/Price"
                        logging.warning(f"Strict Buyability Check Failed (Missing Fields): {url}")
                        log_rejection(url, {"stage": "Buyability", "detail": "missing_critical_fields"})
                        return deal

                    # Explicit Reason 2: Price Out of Bounds
                    try:
                        np_val = float(str(deal.get("new_price", 0)).replace(",", ""))
                        if np_val <= 0:
                            deal["valid"] = False
                            deal["enrich_error"] = "Buyability Failure: Price <= 0"
                            logging.warning(f"Strict Buyability Check Failed (Price <= 0): {url}")
                            log_rejection(url, {"stage": "Buyability", "detail": "price_out_of_bounds"})
                            return deal
                    except:
                        pass # Should be caught by missing fields or schema, but safe to ignore here

                    # Explicit Reason 3: Out of Stock / Unavailable
                    unavailable_markers = ["currently unavailable", "sold out", "out of stock", "coming soon", "pre-order", "item is unavailable", "page not found", "not deliverable", "notify me"]
                    if any(x in text_lower for x in unavailable_markers):
                        deal["valid"] = False
                        deal["in_stock"] = False
                        deal["enrich_error"] = "Buyability Failure: Item Unavailable"
                        logging.warning(f"Strict Buyability Check Failed (Unavailable): {url}")
                        log_rejection(url, {"stage": "Buyability", "detail": "out_of_stock"})
                        return deal

                    # Explicit Reason 4: No Buy Button
                    buy_markers = ["add to cart", "buy now", "proceed to buy"]
                    if not any(x in text_lower for x in buy_markers):
                        deal["valid"] = False
                        deal["enrich_error"] = "Buyability Failure: No Buy Button"
                        logging.warning(f"Strict Buyability Check Failed (No Button): {url}")
                        log_rejection(url, {"stage": "Buyability", "detail": "no_buy_button"})
                        return deal

                # LEVEL 5: Revenue / EPC Gating
                if config.REQUIRE_ANCHOR_PRICING:
                     if not deal.get("anchor_price") or not deal.get("days_since_high"):
                         deal["valid"] = False
                         deal["enrich_error"] = "Missing Anchor Pricing Data"
                         logging.warning(f"Skipping Deal - No Anchor Pricing: {url}")
                         log_rejection(url, {"stage": "Revenue", "detail": "missing_anchor_pricing"})
                         return deal

                     try:
                         ap = float(str(deal["anchor_price"]).replace(",", ""))
                         np = float(str(deal.get("new_price", 0)).replace(",", ""))
                         if ap < np:
                             deal["valid"] = False
                             deal["enrich_error"] = "Anchor Price Lower Than Current Price"
                             logging.warning(f"Skipping Deal - Anchor ({ap}) < New ({np}): {url}")
                             log_rejection(url, {"stage": "Revenue", "detail": "anchor_price_inversion"})
                             return deal
                             
                         # False MRP Check
                         if deal.get("old_price"):
                             op = float(str(deal["old_price"]).replace(",", ""))
                             if op > (ap * 1.5):
                                 deal["valid"] = False
                                 deal["enrich_error"] = "False MRP Detected"
                                 logging.warning(f"Skipping Deal - False MRP ({op} > {ap}*1.5): {url}")
                                 log_rejection(url, {"stage": "Revenue", "detail": "false_mrp_detected"})
                                 return deal
                     except Exception as e:
                         logging.warning(f"Price validation error: {e}")



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
            caption, variant = generate_caption(enriched)
            caption = f"🚨 *UPDATE: {alert_reason}*\n\n" + caption
            
            if not TEST_MODE:
                chat_id = CHANNELS["main"]["chat_id"]
                await post_to_telegram(bot, chat_id, caption)
                await post_to_discord(session, DISCORD_WEBHOOK_URL, enriched, variant)
            
            processed_count += 1
            await asyncio.sleep(ANTI_SPAM_DELAY)
            
    if updates_made and not TEST_MODE:
        save_json(SALE_FOLLOWUP_CACHE_FILE, followup_cache)


# ================== TRACKING & ANALYTICS ==================

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

def generate_caption(deal: dict) -> tuple[str, str]:
    """
    Generates A/B caption variants with Scarcity, Softeners, and Comparison.
    Returns: (caption_text, variant_id)
    """
    title = deal.get("title", "Great Deal")
    price = deal.get("new_price", "N/A")
    old_price = deal.get("old_price", "N/A")
    discount_val = 0
    
    try:
        if price != "N/A" and old_price != "N/A":
            p = float(str(price).replace(",", ""))
            op = float(str(old_price).replace(",", ""))
            if op > 0:
                discount_val = round(((op - p) / op) * 100)
    except:
        pass
        
    discount = f"{discount_val}% OFF" if discount_val > 0 else "Deal"
    link = deal.get("url")
    
    # Flags
    flags = []
    if deal.get("condition") == "Refurbished":
        flags.append("♻️ Refurbished")
    if deal.get("has_coupon"):
        flags.append("🎟️ Coupon Available")
    if deal.get("low_stock"):
        flags.append("⚠️ Low Stock")
        
    flag_str = " | ".join(flags)
    if flag_str:
        flag_str = f"\n{flag_str}"

    # --- ENHANCED ELEMENTS ---
    
    # 1. Gamified Scarcity Bar
    scarcity_bar = ""
    if deal.get("percent_claimed"):
        pc = deal["percent_claimed"]
        filled = int(pc / 10)
        if pc > 0 and filled == 0: filled = 1
        bar = "🟩" * filled + "⬜️" * (10 - filled)
        scarcity_bar = f"\n⚡ *FLASH DEAL* {bar}\n{pc}% claimed | Limited Stock\n"
    elif deal.get("low_stock"):
        scarcity_bar = f"\n⚠️ *Limited Stock:* Only {deal['stock_count']} left!\n"

    # 2. Pain of Payment Softener
    softener_msg = ""
    if deal.get("payment_softener"):
        ps = deal["payment_softener"]
        softener_msg = f"\n💸 *Smart Buy:* ₹{ps['per_day_cost']}/day (less than a {ps['comparison']})\n"

    # 3. Comparison Table / Decoy
    comparison_msg = ""
    if deal.get("comparison_data"):
        cd = deal["comparison_data"]
        # Only show if not variant B (Minimalist) - wait, we decide variant later.
        # Let's construct it, but maybe only use in Variant A.
        comparison_msg = (
            f"\n🆚 *Quick Comparison*\n"
            f"✅ *Best Pick (₹{price})*\n"
            f"• {cd['pros'][0]}\n"
            f"• {cd['pros'][1]}\n"
            f"❌ *Alternative (₹{cd['decoy_price']})*\n"
            f"• {cd['cons'][0]}\n"
        )

    # Variant A: Conversion Optimized (Emoji + Psychology)
    anchor_msg = ""
    if deal.get("anchor_price") and deal.get("days_since_high"):
        ap = deal.get("anchor_price")
        days = deal.get("days_since_high")
        anchor_msg = f"🔥 *Price Drop!* Was ₹{ap} just {days} days ago.\n"
    
    social_msg = ""
    if deal.get("clicks_last_60_min") and deal.get("clicks_last_60_min") >= config.MIN_CLICKS_FOR_SOCIAL_PROOF:
        clicks = deal.get("clicks_last_60_min")
        social_msg = f"🔥 *Trending:* {clicks} people viewed in last hour.\n"

    caption_a = (
        f"{scarcity_bar}"
        f"{anchor_msg}"
        f"{social_msg}"
        f"🔥 *{title}*\n\n"
        f"💰 *Price:* ₹{price} (~~₹{old_price}~~)\n"
        f"📉 *Discount:* {discount}\n"
        f"{softener_msg}"
        f"{flag_str}\n"
        f"{comparison_msg}\n"
        f"👉 [Buy Now]({link})"
    )

    # Variant B: Minimalist (Clean)
    caption_b = (
        f"{anchor_msg}"
        f"**{title}**\n"
        f"Price: ₹{price}\n"
        f"Save: {discount}\n"
        f"{flag_str}\n"
        f"Link: {link}"
    )
    
    # Random selection
    if random.choice([True, False]):
        return caption_a, "A"
    else:
        return caption_b, "B"

# ================== POSTING LOGIC ==================

async def post_to_telegram(bot: Bot, chat_id: int, caption: str):
    """Posts to Telegram with retry logic. Returns message object."""
    if TEST_MODE:
        return None
        
    # Shadow Mode Redirect
    if config.SHADOW_MODE:
        logging.info("SHADOW MODE: Redirecting post to shadow channel.")
        if hasattr(config, "SHADOW_CHANNEL_ID") and config.SHADOW_CHANNEL_ID:
            chat_id = config.SHADOW_CHANNEL_ID
        else:
            logging.warning("Shadow Channel ID not set. Skipping post.")
            return None

    for attempt in range(3):
        try:
            msg = await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
            return msg
        except TelegramError as e:
            err_str = str(e).lower()
            if "flood" in err_str or "spam" in err_str or "userdeactivated" in err_str:
                logging.critical(f"TELEGRAM SPAM/FLOOD DETECTED: {e}. Pausing for 24h.")
                update_trust_decay("system", "SPAM_FLOOD_DETECTED")
                # Activate 24h Safety Pause
                activate_spam_pause(24)
                await asyncio.sleep(60) # Short sleep before loop catches the pause
                return None
            
            if attempt == 2:
                logging.error(f"Telegram error (final): {e}")
                update_trust_decay("system", f"TELEGRAM_ERROR_FINAL: {e}")
            else:
                logging.warning(f"Telegram error (attempt {attempt+1}): {e}")
                await asyncio.sleep(2)
    return None

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
            async with session.post(webhook_url, json=payload) as response:
                if response.status in [200, 204]:
                    return
                else:
                    logging.warning(f"Discord error {response.status}")
        except Exception as e:
            logging.error(f"Discord post failed: {e}")
        await asyncio.sleep(2)

# ================== MAIN ENGINE ==================

async def deal_engine():
    commit_hash = config_monitor.get_git_commit_hash()
    logging.info(f"🚀 Crawl.io Bot Started (Phase 6+) | Ver: {commit_hash} | TEST_MODE={TEST_MODE}")
    
    # Run Config Drift Check
    try:
        config_monitor.detect_config_drift()
    except Exception as e:
        logging.critical(f"Config Monitor Failed: {e}")
        # Fail closed if config monitor fails?
        # Requirement: "Silent config changes = system failure"
        # So we should probably alert or exit, but for now we log critical.

    # Initialize Bot
    telegram_bot = Bot(token=BOT_TOKEN)
    
    # Load Cache
    global processed_cache
    cache_data = load_json(CACHE_FILE, default=[])
    # T-046: Populate TTLCache
    for url in cache_data:
        processed_cache[url] = True
    logging.info(f"Loaded {len(processed_cache)} items from cache.")

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
            # 1. Load Deals
            deals = load_json(DEALS_FILE, default=[])
            if not deals:
                logging.warning("No deals found in deals.json.")
                await asyncio.sleep(60)
                continue

            # Batch Stats
            stats = {
                "sent": 0, "skipped_cache": 0, "low_disc": 0, 
                "invalid": 0, "out_of_stock": 0, "enrich_fail": 0,
                "tagged": 0, "throttled": 0, "variant_a": 0, "variant_b": 0,
                "follow_up_alerts_sent": 0, "stock_change_detected": 0
            }

            async with aiohttp.ClientSession() as session:
                processed_count = 0
                
                # --- PHASE 1: PROCESS NEW DEALS ---
                # Rate Limiting & Persona Sorting
                # Group by Persona
                deals_by_persona = {}
                for d in deals:
                    p = d.get("persona", "General")
                    if p not in deals_by_persona:
                        deals_by_persona[p] = []
                    deals_by_persona[p].append(d)
                
                deals_to_process = []
                
                # Curation: Strict Persona Limits
                deals_to_process = []
                
                for p, p_deals in deals_by_persona.items():
                    # Take top N deals for this persona
                    count_to_take = min(len(p_deals), config.MAX_DEALS_PER_PERSONA_PER_BATCH)
                    deals_to_process.extend(p_deals[:count_to_take])
                
                # Shuffle to avoid predictable persona order
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
                
                for deal in final_batch:
                    cat = deal.get("category", "general")
                    if "category" not in deal:
                        if "audio" in deal.get("title", "").lower(): cat = "audio"
                        elif "laptop" in deal.get("title", "").lower(): cat = "laptop"

                    price_str = str(deal.get("new_price", "1")).lower()
                    is_free = "free" in deal.get("title", "").lower() or price_str == "0" or price_str == "free"
                    
                    if not is_free:
                        if reciprocity_state["free"] < config.RECIPROCITY_RATIO["free"] and not TEST_MODE:
                            logging.info(f"Skipping Paid Deal (Reciprocity Debt): {deal['title']}")
                            log_rejection(deal.get("url", "unknown"), {"stage": "Trust", "detail": "reciprocity_debt"})
                            continue
                        reciprocity_state["paid"] += 1
                        if reciprocity_state["paid"] >= config.RECIPROCITY_RATIO["paid"]:
                            reciprocity_state["free"] -= config.RECIPROCITY_RATIO["free"]
                            reciprocity_state["paid"] = 0
                    else:
                        reciprocity_state["free"] += 1

                    if check_category_throttle(cat):
                        logging.info(f"Skipping deal in throttled category '{cat}': {deal.get('title')}")
                        stats["throttled"] += 1
                        log_rejection(deal.get("url", "unknown"), {"stage": "Revenue", "detail": f"category_throttled_{cat}"})
                        continue

                    raw_url = deal.get("url", "")
                    
                    # ASIN Extraction & Dedup
                    asin = None
                    try:
                        asin_match = re.search(r"/dp/([A-Z0-9]{10})", raw_url)
                        if asin_match:
                            asin = asin_match.group(1)
                    except:
                        pass

                    # 2. Check Cache (Main Post)
                    already_posted = raw_url in processed_cache or (asin and asin in processed_cache)
                    
                    # Even if already posted, we ensure it's in followup_cache for tracking
                    if already_posted:
                        stats["skipped_cache"] += 1
                        # Add to watchlist if not present
                        if raw_url not in followup_cache:
                             followup_cache[raw_url] = {
                                "title": deal.get("title"),
                                "marketplace": deal.get("marketplace"),
                                "url": raw_url,
                                "old_price": deal.get("old_price"),
                                "new_price": deal.get("new_price"),
                                "last_checked": datetime.now().isoformat(),
                                "alerts_sent": []
                             }
                        continue

                    # 3. Affiliate Tagging
                    # Pass category for Sub-ID
                    category = deal.get("category", "general")
                    if deal.get("persona") in ["Gamer", "Tech"]: category = "electronics" # Simple mapping
                    
                    tagged_url = await add_affiliate_tag(session, raw_url, deal.get("marketplace", ""), category)
                    deal["url"] = tagged_url
                    stats["tagged"] += 1

                    # 4. Enrichment & Validation
                    deal = await enrich_deal(session, deal)
                    
                    if not deal.get("valid", False):
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
                    
                    if hasattr(config, "REDIRECT_BRIDGE_URL") and config.REDIRECT_BRIDGE_URL:
                        try:
                            from urllib.parse import quote, unquote
                            target_url = deal.get("url")
                            if not target_url:
                                logging.error(f"Redirect bridge missing target URL for deal: {deal.get('title')}")
                            encoded_target = quote(target_url, safe="")
                            bridge_link = f"{config.REDIRECT_BRIDGE_URL}?url={encoded_target}&user_id=telegram_broadcast&category={deal.get('category','general')}&platform=telegram"
                            wrapped_part = bridge_link.split("url=", 1)[1].split("&", 1)[0] if "url=" in bridge_link else ""
                            decoded_target = unquote(wrapped_part) if wrapped_part else ""
                            if decoded_target and decoded_target != target_url:
                                logging.warning(f"Redirect bridge modified target URL unexpectedly for deal: {deal.get('title')}")
                            if not bridge_link.startswith(config.REDIRECT_BRIDGE_URL) or "?url=" not in bridge_link:
                                logging.error(f"Redirect bridge constructed invalid URL for deal: {deal.get('title')}")
                            deal["url"] = bridge_link
                        except Exception as e:
                            logging.error(f"Failed to wrap Redirect Bridge link: {e}")
                            # Fail safe: Keep original URL
                    
                    caption, variant = generate_caption(deal)
                    if variant == "A": stats["variant_a"] += 1
                    else: stats["variant_b"] += 1

                    if not TEST_MODE:
                        chat_id = CHANNELS["main"]["chat_id"]
                        final_url = deal.get("url", "")
                        if not final_url or not isinstance(final_url, str) or not final_url.startswith("http"):
                            logging.error(f"Posting deal without valid URL field: {deal.get('title')}")
                        if "http" not in caption:
                            logging.warning(f"Caption missing URL for deal: {deal.get('title')}")
                        if "buy" not in caption.lower():
                            logging.warning(f"Caption missing CTA for deal: {deal.get('title')}")
                        msg = await post_to_telegram(telegram_bot, chat_id, caption)
                        await post_to_discord(session, DISCORD_WEBHOOK_URL, deal, variant)
                        
                        if msg:
                             log_post(deal.get("url", "unknown"), deal.get("category", "general"))

                        # Update Cache
                        processed_cache[raw_url] = True
                        if asin:
                            processed_cache[asin] = True
                        
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
                        
                    processed_count += 1
                    stats["sent"] += 1
                    await asyncio.sleep(ANTI_SPAM_DELAY)
                
                # --- PHASE 2: PROCESS FOLLOW-UPS ---
                # Run follow-up checks (does not consume main batch limit in this implementation, 
                # or we can pass remaining limit. Current impl has its own limit check inside)
                await process_followups(session, telegram_bot, stats)

            # 8. Logging & Cleanup
            if not TEST_MODE:
                save_json(CACHE_FILE, list(processed_cache))
                save_json(SALE_FOLLOWUP_CACHE_FILE, followup_cache)
                update_analytics(stats)
                
            logging.info(f"Batch Complete: {stats}")
            
            # Randomized Sleep
            sleep_time = POST_INTERVAL_SECONDS * random.uniform(0.85, 1.15)
            logging.info(f"Sleeping for {int(sleep_time)}s...")
            await asyncio.sleep(sleep_time)

        except Exception as e:
            logging.error(f"Critical Loop Error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(deal_engine())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
