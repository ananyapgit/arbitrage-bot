import os
import sys
from dotenv import load_dotenv
load_dotenv("secrets.env")


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ================== CONFIGURATION ==================

# Secrets (In production, load these from env vars)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("CRITICAL ERROR: BOT_TOKEN is missing from environment variables.")
    sys.exit(1)

# Telegram Config
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
EDUCATION_CHANNEL_ID = os.getenv("EDUCATION_CHANNEL_ID")
DEALS_CHANNEL_ID = os.getenv("DEALS_CHANNEL_ID")

# Fallbacks
if not DEALS_CHANNEL_ID:
    DEALS_CHANNEL_ID = TELEGRAM_CHAT_ID

if not EDUCATION_CHANNEL_ID:
    EDUCATION_CHANNEL_ID = TELEGRAM_CHAT_ID

# Sanitization
if TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = str(TELEGRAM_CHAT_ID)
if DEALS_CHANNEL_ID:
    DEALS_CHANNEL_ID = str(DEALS_CHANNEL_ID)
if EDUCATION_CHANNEL_ID:
    EDUCATION_CHANNEL_ID = str(EDUCATION_CHANNEL_ID)

if TELEGRAM_CHAT_ID:
    print(f"DEBUG: Posting to Channel ID {TELEGRAM_CHAT_ID}")

CHANNELS = {
    "main": {
        "chat_id": DEALS_CHANNEL_ID,
        "categories": ["audio", "accessory", "laptop", "general"]
    },
    "education": {
        "chat_id": EDUCATION_CHANNEL_ID,
        "categories": ["course", "education", "book"]
    }
}
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "placeholder_disabled")
HIGH_EPC_CATEGORIES = ["electronics"]

def env_int(key, default):
    try:
        return int(os.getenv(key, str(default)))
    except Exception:
        return default

def env_float(key, default):
    try:
        return float(os.getenv(key, str(default)))
    except Exception:
        return default

# Bot Behavior
POST_INTERVAL_SECONDS = env_int("POST_INTERVAL_SECONDS", 900)
ANTI_SPAM_DELAY = env_int("ANTI_SPAM_DELAY", 5)
MAX_DEALS_PER_BATCH = env_int("MAX_DEALS_PER_BATCH", 10)
MIN_DISCOUNT_THRESHOLD = env_float("MIN_DISCOUNT_THRESHOLD", 5.0)

def env_bool(key, default):
    return os.getenv(key, str(default)).lower() == "true"

TEST_MODE = env_bool("TEST_MODE", False)
DRY_RUN = env_bool("DRY_RUN", False)
SINGLE_RUN = env_bool("SINGLE_RUN", False) # Revenue Priority: Set to False for continuous run

SCRAPE_INTERVAL_SECONDS = 5


# Follow-up & Dynamic Polling
SALE_POLL_INTERVAL_MINUTES = 10
STOCK_ALERT_THRESHOLDS = [50, 20, 10, 5] # Triggers at 50%, 20%, 10% stock or 5 items left
FOLLOW_UP_SLEEP_SECONDS = 600
SALE_FOLLOWUP_CACHE_FILE = "sale_followup_cache.json"
WAITLIST_DB_FILE = "waitlist_db.json"

# Conversion & Trust Engine
STRICT_BUYABILITY_CHECK = False # Revenue Priority: Relaxed
RECIPROCITY_RATIO = {"free": 3, "paid": 1} # 3 Free : 1 Paid
RETARGETING_WINDOW_MINUTES = 90
MENTAL_ACCOUNTING_THRESHOLD = 199 # Apply logic for items above this price

# Enhanced Rules
MAX_DEALS_PER_PERSONA_PER_BATCH = 100 # Revenue Priority: Increased
FOLLOW_UP_COOLDOWN_HOURS = 3
MAX_FOLLOW_UPS_PER_DEAL = 3
MIN_CLICKS_FOR_SOCIAL_PROOF = 20
REQUIRE_ANCHOR_PRICING = False # Revenue Priority: Disabled

# Shadow & Chaos Mode
SHADOW_MODE = os.getenv("SHADOW_MODE", "false").lower() == "true"
POST_GUARD = os.getenv("POST_GUARD", "true").lower() == "true"

# Fallback to main chat if shadow not set
SHADOW_CHANNEL_ID = os.getenv("SHADOW_CHANNEL_ID")
if SHADOW_CHANNEL_ID:
    try:
        SHADOW_CHANNEL_ID = int(SHADOW_CHANNEL_ID)
    except ValueError:
        SHADOW_CHANNEL_ID = TELEGRAM_CHAT_ID
else:
    SHADOW_CHANNEL_ID = TELEGRAM_CHAT_ID

TRUST_RATING_THRESHOLD = 4.0
MAX_SHIPPING_PERCENT = 0.20
PRICE_ERROR_DROP_THRESHOLD = 0.80
SCRAPE_INTERVAL_MIN = 45
SCRAPE_INTERVAL_MAX = 75

# Revenue Protection (Sub-IDs)
EPC_THROTTLE_THRESHOLD = 0.10 # Pause category if EPC < $0.10

REDIRECT_PUBLIC_URL = os.getenv("REDIRECT_PUBLIC_URL", "https://redirect-service-kyf0.onrender.com/r")
REDIRECT_BRIDGE_URL = REDIRECT_PUBLIC_URL

SUB_IDS = {
    "electronics": "elec_001",
    "fashion": "fash_001",
    "home": "home_001",
    "general": "gen_001"
}

# Affiliate Tags
AFFILIATE_TAGS = {
    "amazon.in": os.getenv("AMAZON_TAG"),
    "flipkart.com": os.getenv("FLIPKART_TAG"),
}

# File Paths
DEALS_FILE = "deals.json"
CACHE_FILE = "cache.json"
LANDING_PAGE_FILE = "site/deals.json"
REDDIT_DRAFT_FILE = "reddit_drafts.json"
ANALYTICS_FILE = "analytics.json"
