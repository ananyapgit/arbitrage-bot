import os

# ================== CONFIGURATION ==================

# Secrets (In production, load these from env vars)
BOT_TOKEN = "8529561535:AAGH88AnbX7G6xepaDh4a7tC-IWyg35YbN0"
CHANNELS = {
    "main": {
        "chat_id": -1003561797352,
        "categories": ["audio", "accessory", "laptop", "general"]
    }
}
DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE" 

# Bot Behavior
POST_INTERVAL_SECONDS = 900  # 15 minutes
ANTI_SPAM_DELAY = 5
MAX_DEALS_PER_BATCH = 10  # Throttle
MIN_DISCOUNT_THRESHOLD = 5.0 
DRY_RUN = False 
TEST_MODE = True  # TEST MODE DEFAULT for Safety

# Follow-up & Dynamic Polling
SALE_POLL_INTERVAL_MINUTES = 10
STOCK_ALERT_THRESHOLDS = [50, 20, 10, 5] # Triggers at 50%, 20%, 10% stock or 5 items left
FOLLOW_UP_SLEEP_SECONDS = 600
SALE_FOLLOWUP_CACHE_FILE = "sale_followup_cache.json"

# Conversion & Trust Engine
STRICT_BUYABILITY_CHECK = True
RECIPROCITY_RATIO = {"free": 3, "paid": 1} # 3 Free : 1 Paid
RETARGETING_WINDOW_MINUTES = 90
MENTAL_ACCOUNTING_THRESHOLD = 199 # Apply logic for items above this price

# Enhanced Rules
MAX_DEALS_PER_PERSONA_PER_BATCH = 1
FOLLOW_UP_COOLDOWN_HOURS = 3
MAX_FOLLOW_UPS_PER_DEAL = 3
MIN_CLICKS_FOR_SOCIAL_PROOF = 20
REQUIRE_ANCHOR_PRICING = True

# Shadow & Chaos Mode
SHADOW_MODE = False
SHADOW_CHANNEL_ID = -1001234567890 # Replace with actual private channel
TRUST_RATING_THRESHOLD = 4.0
MAX_SHIPPING_PERCENT = 0.20
PRICE_ERROR_DROP_THRESHOLD = 0.80
SCRAPE_INTERVAL_MIN = 45
SCRAPE_INTERVAL_MAX = 75

# Revenue Protection (Sub-IDs)
EPC_THROTTLE_THRESHOLD = 0.10 # Pause category if EPC < $0.10
REDIRECT_BRIDGE_URL = "http://localhost:8080/r" # Redirect Bridge
SUB_IDS = {
    "electronics": "elec_001",
    "fashion": "fash_001",
    "home": "home_001",
    "general": "gen_001"
}

# Affiliate Tags
AFFILIATE_TAGS = {
    "amazon.in": "crawl0f-21",
    "flipkart.com": "affid",
}

# File Paths
DEALS_FILE = "deals.json"
CACHE_FILE = "cache.json"
LANDING_PAGE_FILE = "site/deals.json"
REDDIT_DRAFT_FILE = "reddit_drafts.json"
ANALYTICS_FILE = "analytics.json"
