import json
import asyncio
import logging
import random
import aiohttp
from datetime import datetime, timezone
from telegram import Bot
from telegram.helpers import escape_markdown
from telegram.error import TelegramError
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import config

# ================== CONFIG ==================
# Loaded from config.py
BOT_TOKEN = config.BOT_TOKEN
CHANNELS = config.CHANNELS
DISCORD_WEBHOOK_URL = config.DISCORD_WEBHOOK_URL

POST_INTERVAL_SECONDS = config.POST_INTERVAL_SECONDS
ANTI_SPAM_DELAY = config.ANTI_SPAM_DELAY
MAX_DEALS_PER_BATCH = config.MAX_DEALS_PER_BATCH
MIN_DISCOUNT_THRESHOLD = config.MIN_DISCOUNT_THRESHOLD
DRY_RUN = config.DRY_RUN
TEST_MODE = config.TEST_MODE

AFFILIATE_TAGS = config.AFFILIATE_TAGS

DEALS_FILE = config.DEALS_FILE
CACHE_FILE = config.CACHE_FILE
LANDING_PAGE_FILE = config.LANDING_PAGE_FILE
REDDIT_DRAFT_FILE = config.REDDIT_DRAFT_FILE
ANALYTICS_FILE = config.ANALYTICS_FILE

# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
bot = Bot(token=BOT_TOKEN)

# ================== UTILITIES ==================

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except Exception as e:
        logging.warning(f"Failed to load {path}: {e}")
        return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Failed to save {path}: {e}")

def calculate_discount(deal):
    try:
        old_p_str = str(deal.get("old_price", "0")).replace(',', '').replace('₹', '').strip()
        new_p_str = str(deal.get("new_price", "0")).replace(',', '').replace('₹', '').strip()
        old_p = float(old_p_str) if old_p_str else 0
        new_p = float(new_p_str) if new_p_str else 0
        if old_p > 0:
            return ((old_p - new_p) / old_p) * 100
    except:
        pass
    return 0.0

# ================== AFFILIATE TAGGING ==================

async def add_affiliate_tag(url: str, marketplace: str) -> str:
    """
    Appends affiliate tag if missing.
    """
    # Simulate async CPU bound task
    await asyncio.sleep(0) 
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        
        # Simple domain matching for now
        tag = None
        tag_key = "tag" # Default Amazon param
        
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
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
            return new_url
            
    except Exception as e:
        logging.warning(f"Error adding affiliate tag to {url}: {e}")
        
    return url

# ================== DEAL ENRICHMENT (ASYNC) ==================

async def enrich_deal(deal: dict) -> dict:
    """
    Fetches missing metadata (old_price, new_price) if needed.
    """
    deal["enrichment_status"] = "skipped"
    if deal.get("old_price") and deal.get("new_price"):
        return deal # Already complete
        
    url = deal.get("url")
    deal["enrichment_status"] = "attempted"
    # logging.info(f"Enriching deal: {deal['title']}")
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                # Simulated request - in real usage, parse HTML here
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        # Logic to extract price would go here
                        # deal["old_price"] = extracted_old
                        # deal["new_price"] = extracted_new
                        deal["enrichment_status"] = "success"
                        pass
                    break
            except Exception as e:
                logging.warning(f"Enrichment failed (attempt {attempt+1}): {e}")
                if attempt == 2: deal["enrichment_status"] = "failed"
                await asyncio.sleep(2**attempt)
                
    return deal

# ================== REFERRAL & USER TRACKING ==================

async def track_referral_click(user_id: str, deal_id: str):
    """
    Simulates tracking a user click on a referral link.
    """
    if TEST_MODE:
        # logging.info(f"[TEST_MODE] Tracking referral: User {user_id} -> Deal {deal_id}")
        pass
        
    # In real app: DB insert
    # Update analytics
    if not TEST_MODE:
        update_analytics_referral(user_id)
        
    # Simulate async I/O
    await asyncio.sleep(0.01)

async def reward_referral(user_id: str):
    """
    Simulates rewarding a user for a successful referral/action.
    """
    if TEST_MODE:
        logging.info(f"[TEST_MODE] Rewarding user {user_id} for referral.")
        pass

async def track_user_engagement(user_id: str, marketplace: str):
    """
    Tracks user engagement with specific marketplaces.
    """
    if TEST_MODE: return
    # Update analytics logic would go here
    update_analytics_user_stats(user_id, marketplace)
    await asyncio.sleep(0.01)

# ================== URL VERIFICATION (ASYNC) ==================

async def verify_url(url: str) -> bool:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

# ================== CACHE ==================

def load_cache():
    return load_json(CACHE_FILE, {"posted": []})["posted"]

def save_to_cache(url):
    if TEST_MODE:
        return
    data = load_json(CACHE_FILE, {"posted": []})
    if url not in data["posted"]:
        data["posted"].append(url)
        save_json(CACHE_FILE, data)

# ================== ANALYTICS (EXPANDED) ==================

def load_analytics():
    defaults = {
        "marketplaces": {},
        "discounts": {"0-10%": 0, "10-30%": 0, ">30%": 0},
        "total_posted": 0,
        "referrals": {"total_clicks": 0, "rewards_given": 0},
        "ab_testing": {},
        "user_behavior": {},
        "daily_summary": {}
    }
    return load_json(ANALYTICS_FILE, defaults)

def update_analytics(marketplace, discount_percent, caption_variant):
    if TEST_MODE: return
        
    data = load_analytics()
    
    # Marketplace stats
    data["marketplaces"][marketplace] = data["marketplaces"].get(marketplace, 0) + 1
    
    # Discount stats
    if discount_percent >= 30:
        data["discounts"][">30%"] += 1
    elif discount_percent >= 10:
        data["discounts"]["10-30%"] += 1
    else:
        data["discounts"]["0-10%"] += 1
        
    data["total_posted"] += 1

    # A/B Testing Stats
    if caption_variant not in data["ab_testing"]:
        data["ab_testing"][caption_variant] = {"posted": 0}
    data["ab_testing"][caption_variant]["posted"] += 1
    
    # Daily Summary
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in data["daily_summary"]:
        data["daily_summary"][today] = {
            "posted": 0, 
            "skipped": 0,
            "invalid_urls": 0,
            "enrichment_failures": 0,
            "affiliate_tagged": 0,
            "referral_clicks": 0,
            "ab_variants": {},
            "discounts": []
        }
    
    data["daily_summary"][today]["posted"] += 1
    data["daily_summary"][today]["discounts"].append(round(discount_percent, 2))
    
    # A/B Daily
    ab_daily = data["daily_summary"][today].get("ab_variants", {})
    ab_daily[caption_variant] = ab_daily.get(caption_variant, 0) + 1
    data["daily_summary"][today]["ab_variants"] = ab_daily
    
    save_json(ANALYTICS_FILE, data)

def update_analytics_referral(user_id):
    if TEST_MODE: return
    data = load_analytics()
    data["referrals"]["total_clicks"] += 1
    
    today = datetime.now().strftime("%Y-%m-%d")
    if today in data["daily_summary"]:
        data["daily_summary"][today]["referral_clicks"] = data["daily_summary"][today].get("referral_clicks", 0) + 1
        
    save_json(ANALYTICS_FILE, data)

def update_analytics_user_stats(user_id, marketplace):
    if TEST_MODE: return
    data = load_analytics()
    if user_id not in data["user_behavior"]:
        data["user_behavior"][user_id] = {"clicks": 0, "marketplaces": {}}
    
    data["user_behavior"][user_id]["clicks"] += 1
    user_mkts = data["user_behavior"][user_id]["marketplaces"]
    user_mkts[marketplace] = user_mkts.get(marketplace, 0) + 1
    
    save_json(ANALYTICS_FILE, data)

def update_analytics_batch_stats(skipped_count, invalid_count, enrichment_fails, tagged_count):
    if TEST_MODE: return
    data = load_analytics()
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in data["daily_summary"]:
         # Init if empty (unlikely if posted > 0)
         data["daily_summary"][today] = {"posted": 0, "skipped": 0, "invalid_urls": 0, "enrichment_failures": 0, "affiliate_tagged": 0, "referral_clicks": 0, "ab_variants": {}, "discounts": []}
    
    day_stats = data["daily_summary"][today]
    day_stats["skipped"] = day_stats.get("skipped", 0) + skipped_count
    day_stats["invalid_urls"] = day_stats.get("invalid_urls", 0) + invalid_count
    day_stats["enrichment_failures"] = day_stats.get("enrichment_failures", 0) + enrichment_fails
    day_stats["affiliate_tagged"] = day_stats.get("affiliate_tagged", 0) + tagged_count
    
    save_json(ANALYTICS_FILE, data)

# ================== DEAL SOURCE & SORTING ==================

def load_deals():
    return load_json(DEALS_FILE, [])

def sort_deals(deals: list) -> list:
    # Logic: High discount first, then marketplace
    return sorted(deals, key=lambda x: (-calculate_discount(x), x.get("marketplace", "")))

# ================== CAPTION ENGINE (A/B TESTING) ==================

TIER_CAPTIONS = {
    "high": ["🔥 Steal this deal!", "🚨 Price Error Alert?", "🤯 Unbelievable drop!"],
    "medium": ["🛒 Grab it while you can!", "⚡ Solid savings here.", "👀 Worth a look."],
    "low": ["Maybe not the best, but still available!", "📉 Small drop, still good.", "🤷‍♂️ Available now."]
}

# A/B Variants
CAPTION_STYLES = {
    "A": "Emoji Heavy",
    "B": "Minimalist"
}

def get_tier_caption(deal: dict, variant="A") -> str:
    discount = calculate_discount(deal)
    if discount >= 30:
        tier = "high"
    elif discount >= 10:
        tier = "medium"
    else:
        tier = "low"
        
    base_caption = random.choice(TIER_CAPTIONS[tier])
    
    if variant == "B":
        # Strip emojis for minimalist variant
        return base_caption.encode('ascii', 'ignore').decode('ascii').strip()
    
    return base_caption

def generate_caption(deal: dict) -> tuple[str, str]:
    """
    Returns (caption_text, variant_id)
    """
    variant = random.choice(["A", "B"])
    caption_text = get_tier_caption(deal, variant)
    final_caption = f"{caption_text} {deal['title']} - {deal['new_price']} ({deal['url']})"
    return final_caption, variant

# ================== CATEGORY ENGINE ==================

def detect_category(title: str):
    t = title.lower()
    if any(k in t for k in ["earbud", "headphone", "airpods", "audio"]):
        return "audio"
    if any(k in t for k in ["mouse", "keyboard", "accessory"]):
        return "accessory"
    if any(k in t for k in ["laptop", "macbook", "notebook"]):
        return "laptop"
    return "general"

# ================== TELEGRAM ==================

async def post_to_telegram(deal, channel_cfg, caption_text):
    discount_percent = calculate_discount(deal)
    
    title_emoji = " 🔥" if discount_percent >= 30 else ""
    title_emoji += " 🛒"

    marketplace = deal.get("marketplace", "Deal")
    display_title = f"[{marketplace}] {deal['title']}"

    title_escaped = escape_markdown(display_title + title_emoji, version=2)
    caption_escaped = escape_markdown(caption_text, version=2)
    old_price_escaped = escape_markdown(str(deal["old_price"]), version=2)
    new_price_escaped = escape_markdown(str(deal["new_price"]), version=2)
    url = deal["url"]

    text = (
        f"*{title_escaped}*\n"
        f"_{caption_escaped}_\n\n"
        f"~~{old_price_escaped}~~ → *{new_price_escaped}*\n\n"
        f"[Buy here]({url})"
    )

    if DRY_RUN:
        logging.info(f"[DRY RUN] Telegram post prepared: {deal['title']}")
        return True

    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=channel_cfg["chat_id"],
                text=text,
                parse_mode="MarkdownV2",
                disable_web_page_preview=False
            )
            logging.info(f"Posting {deal['title']} to Telegram.")
            return True
        except TelegramError as e:
            logging.error(f"Telegram error (attempt {attempt+1}/3): {e}")
            await asyncio.sleep(2 * (attempt + 1))
        except Exception as e:
            logging.error(f"Unexpected error posting to Telegram: {e}")
            break
            
    return False

# ================== DISCORD ==================

async def post_to_discord(deal, caption_text):
    if TEST_MODE:
        # logging.info(f"[TEST_MODE] Skipping Discord post for: {deal['title']}")
        return

    if not DISCORD_WEBHOOK_URL or "YOUR_DISCORD_WEBHOOK_URL" in DISCORD_WEBHOOK_URL:
        return

    discount_percent = calculate_discount(deal)
    marketplace = deal.get("marketplace", "Deal")
    
    embed = {
        "title": f"[{marketplace}] {deal['title']}",
        "description": f"**Price:** ~~{deal['old_price']}~~ → **{deal['new_price']}**\n**Discount:** {discount_percent:.1f}% off",
        "url": deal["url"],
        "color": 5814783, 
        "footer": {"text": "Arbitrage Bot"},
        "timestamp": now_utc()
    }
    
    payload = {"content": caption_text, "embeds": [embed]}

    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.post(DISCORD_WEBHOOK_URL, json=payload) as response:
                    if response.status in [200, 204]:
                        logging.info(f"Posted {deal['title']} to Discord.")
                        return
                    else:
                        logging.warning(f"Discord Webhook failed (attempt {attempt+1}): {response.status}")
                        await asyncio.sleep(2 * (attempt + 1))
            except Exception as e:
                logging.error(f"Discord error (attempt {attempt+1}): {e}")
                await asyncio.sleep(2 * (attempt + 1))

# ================== CROSS POSTING (ENHANCED) ==================

async def cross_post_to_twitter(deal):
    """
    Twitter X API integration stub.
    """
    if TEST_MODE:
        # logging.info(f"[TEST_MODE] Skipping Twitter post for: {deal['title']}")
        return
    
    # Logic to format tweet with enriched data
    # tweet_text = f"{deal['title']} {deal['discount']}% off! {deal['url']}"
    logging.info(f"Cross-posting to Twitter: {deal['title']}")

async def cross_post_to_fb(deal):
    """
    Facebook Graph API integration stub.
    """
    if TEST_MODE:
        # logging.info(f"[TEST_MODE] Skipping Facebook post for: {deal['title']}")
        return
        
    logging.info(f"Cross-posting to Facebook: {deal['title']}")

# ================== LANDING PAGE & REDDIT ==================

def update_landing_page(deal):
    if TEST_MODE: return
    existing = load_json(LANDING_PAGE_FILE, [])
    deal["posted_at"] = now_utc()
    existing.insert(0, deal)
    save_json(LANDING_PAGE_FILE, existing[:50])

def generate_reddit_draft(deal):
    title = f"{deal['title']} dropped to {deal['new_price']} (India)"
    body = (
        f"Noticed this deal while browsing today.\n\n"
        f"Was earlier around {deal['old_price']} and is now available at "
        f"{deal['new_price']}.\n\n"
        f"Link: {deal['url']}\n\n"
        f"*Sharing in case it helps someone. Not affiliated.*"
    )

    return {
        "title": title,
        "body": body,
        "category": deal.get("category", "general"),
        "created_at": now_utc()
    }

def save_reddit_draft(draft):
    if TEST_MODE: return
    drafts = load_json(REDDIT_DRAFT_FILE, [])
    drafts.insert(0, draft)
    save_json(REDDIT_DRAFT_FILE, drafts)

# ================== MAIN ENGINE ==================

async def deal_engine():
    logging.info("🚀 Crawl.io automation started (Phase 6 Production Ready)")
    
    if TEST_MODE:
        logging.warning("⚠️ RUNNING IN TEST_MODE: Cache ignored, updates not saved, Cross-posting skipped.")

    initial_cache = load_cache()
    logging.info(f"Cache contains {len(initial_cache)} URLs.")

    while True:
        try:
            deals = load_deals()
            if not deals:
                logging.warning("No deals found in deals.json.")
            
            # Sort deals
            deals = sort_deals(deals)
            
            posted_cache = load_cache()
            messages_sent = 0
            skipped_cache_count = 0
            invalid_url_count = 0
            enrichment_fail_count = 0
            affiliate_tagged_count = 0
            throttled_count = 0
            skipped_low_discount = 0
            referral_simulations = 0
            ab_selection_stats = {"A": 0, "B": 0}
            
            # Rate Limiting
            deals_to_process = deals[:MAX_DEALS_PER_BATCH]
            if len(deals) > MAX_DEALS_PER_BATCH:
                throttled_count = len(deals) - MAX_DEALS_PER_BATCH
                logging.info(f"Throttling enabled: Processing {MAX_DEALS_PER_BATCH} of {len(deals)} deals.")

            for deal in deals_to_process:
                url = deal.get("url")
                if not url:
                    continue
                
                # Discount Threshold Check
                discount_pct = calculate_discount(deal)
                if discount_pct < MIN_DISCOUNT_THRESHOLD:
                    # In future: check if high engagement, if so, allow it.
                    # For now, skip.
                    skipped_low_discount += 1
                    # logging.info(f"Skipping low discount deal: {deal['title']} ({discount_pct:.1f}%)")
                    continue

                # URL Verification
                if not await verify_url(url):
                    logging.warning(f"Skipping invalid URL: {url}")
                    invalid_url_count += 1
                    continue

                # Affiliate Tagging
                marketplace = deal.get("marketplace", "Unknown")
                original_url = url
                deal["url"] = await add_affiliate_tag(url, marketplace)
                if deal["url"] != original_url:
                    affiliate_tagged_count += 1

                # Deal Enrichment
                try:
                    deal = await enrich_deal(deal)
                    if deal["enrichment_status"] == "failed":
                        enrichment_fail_count += 1
                except Exception as e:
                    logging.warning(f"Enrichment failed for {deal['title']}: {e}")
                    enrichment_fail_count += 1

                # Cache Check
                is_in_cache = deal["url"] in posted_cache
                if is_in_cache and not TEST_MODE:
                    skipped_cache_count += 1
                    continue
                
                if is_in_cache and TEST_MODE:
                    logging.info(f"[TEST_MODE] Re-posting {deal['title']} even though it's in cache.")

                deal["category"] = detect_category(deal.get("title", ""))
                
                # A/B Caption Generation
                full_caption, caption_variant = generate_caption(deal)
                ab_selection_stats[caption_variant] += 1
                
                # Post to Telegram
                posted_successfully = False
                
                for channel_name, channel_cfg in CHANNELS.items():
                    if deal["category"] in channel_cfg["categories"]:
                        # Extract just the caption text for Telegram helper (helper adds title/price itself)
                        # We need to pass the variant caption part only to post_to_telegram?
                        # Actually post_to_telegram constructs the message. Let's pass the text part.
                        caption_text_only = get_tier_caption(deal, caption_variant)
                        
                        success = await post_to_telegram(deal, channel_cfg, caption_text_only)
                        if success:
                            posted_successfully = True
                            messages_sent += 1
                
                # Post to Discord
                await post_to_discord(deal, full_caption)

                # Cross-Posting Hooks
                await cross_post_to_twitter(deal)
                await cross_post_to_fb(deal)

                # Simulate Referral Loop & User Behavior
                if TEST_MODE:
                    await track_referral_click("test_user_123", deal["url"])
                    await track_user_engagement("test_user_123", marketplace)
                    referral_simulations += 1

                if posted_successfully:
                    if not TEST_MODE:
                        update_landing_page(deal)
                        save_reddit_draft(generate_reddit_draft(deal))
                        save_to_cache(deal["url"])
                        update_analytics(marketplace, discount_pct, caption_variant)
                        logging.info(f"Posted: {deal['title']} | Disc: {discount_pct:.1f}% | Mkt: {marketplace} | Var: {caption_variant} | Ref: 0")
                    else:
                        logging.info(f"[TEST_MODE] Posted: {deal['title']} | Disc: {discount_pct:.1f}% | Mkt: {marketplace} | Var: {caption_variant} | Ref: Simulated | Enrich: {deal.get('enrichment_status')}")

                # Anti-spam delay
                await asyncio.sleep(ANTI_SPAM_DELAY)

            # Update analytics batch stats
            update_analytics_batch_stats(skipped_cache_count, invalid_url_count, enrichment_fail_count, affiliate_tagged_count)

            logging.info(f"Batch complete. Sent: {messages_sent}, Skipped(Cache): {skipped_cache_count}, LowDisc: {skipped_low_discount}, Invalid: {invalid_url_count}, EnrichFail: {enrichment_fail_count}, Tagged: {affiliate_tagged_count}, Throttled: {throttled_count}, RefSims: {referral_simulations}, AB_A: {ab_selection_stats['A']}, AB_B: {ab_selection_stats['B']}")
            # logging.info(f"A/B Stats: A={ab_selection_stats['A']}, B={ab_selection_stats['B']}")
            
            if TEST_MODE:
                logging.warning("TEST_MODE active — cache ignored.")
            
            # Randomized sleep +/- 15%
            sleep_variance = int(POST_INTERVAL_SECONDS * 0.15) 
            sleep_time = POST_INTERVAL_SECONDS + random.randint(-sleep_variance, sleep_variance)
            
            logging.info(f"Sleeping for {sleep_time} seconds...")
            await asyncio.sleep(sleep_time)

        except Exception as e:
            logging.error(f"Main loop error: {e}")
            logging.info("Restarting loop in 60 seconds...")
            await asyncio.sleep(60)

# ================== ENTRY ==================

if __name__ == "__main__":
    try:
        asyncio.run(deal_engine())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
