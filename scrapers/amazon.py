"""
LIVE WEB SCRAPER — NO STATIC DATA
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
import random
import json
import config
from datetime import datetime

# Category rotation for diverse scraping
AMAZON_CATEGORIES = [
    "electronics", "home-kitchen", "fashion", "beauty", "toys", "sports", "books"
]

async def get_amazon_movers_shakers():
    """
    Scrapes Amazon India Movers & Shakers JSON-LD feed for diverse products.
    Rotates through categories to break laptop loop.
    """
    category = random.choice(AMAZON_CATEGORIES)
    url = f"https://www.amazon.in/gp/movers-and-shakers/{category}"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Extract JSON-LD data
                    json_scripts = soup.find_all("script", type="application/ld+json")
                    deals = []
                    
                    for script in json_scripts:
                        try:
                            data = json.loads(script.string)
                            if isinstance(data, list):
                                data = data[0]
                            
                            # Look for product data in Movers & Shakers
                            if data.get("@type") == "ItemList":
                                items = data.get("itemListElement", [])
                                for item in items:
                                    if item.get("@type") == "Product":
                                        product = {
                                            "title": item.get("name"),
                                            "url": item.get("url"),
                                            "price": item.get("offers", {}).get("price"),
                                            "marketplace": "Amazon"
                                        }
                                        if product["title"] and product["url"]:
                                            deals.append(product)
                        except:
                            continue
                    
                    return deals
    except Exception as e:
        print(f"Movers & Shakers scraping failed: {e}")
        return []

async def get_amazon_todays_deals():
    """
    Scrapes Amazon Today's Deals JSON-LD feed for diverse products.
    """
    url = "https://www.amazon.in/gp/goldbox"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Extract deal cards
                    deal_cards = soup.select(".dealCard, .deal-card, .a-deal-card")
                    deals = []
                    
                    for card in deal_cards:
                        link_elem = card.select_one("a[href]")
                        title_elem = card.select_one(".deal-title, .a-deal-card-title")
                        
                        if link_elem and title_elem:
                            url = link_elem.get("href")
                            title = title_elem.get_text(strip=True)
                            
                            if url and title:
                                if url.startswith("/"):
                                    url = "https://www.amazon.in" + url
                                
                                deals.append({
                                    "title": title,
                                    "url": url,
                                    "marketplace": "Amazon"
                                })
                    
                    return deals
    except Exception as e:
        print(f"Today's Deals scraping failed: {e}")
        return []

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.6099.199 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.6100.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
]

async def get_diverse_amazon_deals():
    """
    BREAK THE LAPTOP LOOP: Get diverse Amazon deals from multiple sources.
    Rotates through categories: Electronics, Home, Fashion, Beauty.
    """
    all_deals = []
    
    # Try Movers & Shakers first
    try:
        movers_deals = await get_amazon_movers_shakers()
        all_deals.extend(movers_deals)
    except Exception as e:
        print(f"Movers & Shakers failed: {e}")
    
    # Try Today's Deals as fallback
    try:
        today_deals = await get_amazon_todays_deals()
        all_deals.extend(today_deals)
    except Exception as e:
        print(f"Today's Deals failed: {e}")
    
    return all_deals

async def get_amazon_product(url):
    """
    Fetches product details from a live Amazon URL.
    Returns None if scraping fails or critical data is missing.
    """
    # ANTI-CATEGORY LOGIC: Only process individual product URLs
    from bot import is_individual_product_url
    if not is_individual_product_url(url):
        return None
    
    # ANTI-DETECTION: Random delay between product scrapes (mimic human browsing)
    scrape_delay = random.uniform(2, 5)
    await asyncio.sleep(scrape_delay)

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="140", "Chromium";v="140"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document"
    }

    # Retry up to 5 times on network errors to scrape harder
    async with aiohttp.ClientSession() as session:
        for attempt in range(5):
            try:
                # Use optimized timeout from config
                async with session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT) as response:
                    if response.status == 403:
                        with open("health_check.log", "a") as f:
                            f.write(f"{datetime.now()}: 403 Forbidden for {url}\n")
                        return None
                    response.raise_for_status()
                    html = await response.text()
                    break  # Success, exit retry loop
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == 2:  # Last attempt failed
                    return None
                await asyncio.sleep(random.uniform(1, 3)) # Add jitter between retries
    
    soup = BeautifulSoup(html, "html.parser")
    
    # --- RESILIENT SELECTORS (Amazon March 2026 Update) ---
    title_el = soup.select_one("#productTitle")
    title = title_el.get_text(strip=True) if title_el else None
    
    # Search for price in specified order: .a-price-whole, .a-offscreen, span[data-a-color='price']
    price_el = soup.select_one(".a-price-whole")
    if not price_el:
        price_el = soup.select_one(".a-offscreen")
    if not price_el:
        price_el = soup.select_one("span[data-a-color='price']")
    
    price = price_el.get_text(strip=True) if price_el else None

    # --- AMAZON STEALTH PRECISION: JSON-LD for sku/productID ---
    product_id = None
    try:
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                # Handle both single objects and lists of objects
                if isinstance(data, list):
                    data = data[0]
                
                # Target specific product data with sku/productID
                if data.get("@type") == "Product":
                    if not title and "name" in data:
                        title = data["name"]
                    
                    # Extract product ID for precision
                    if not product_id:
                        product_id = data.get("sku") or data.get("productID") or data.get("mpn")
                    
                    # Extract specific price from offers
                    if not price:
                        offers = data.get("offers")
                        if isinstance(offers, dict):
                            price = offers.get("price")
                            # Validate this is a specific product price, not a range
                            if price and isinstance(price, (int, float, str)):
                                try:
                                    price_val = float(str(price).replace("$", "").replace(",", ""))
                                    # Discard if price is too low (likely error) or too high (category page)
                                    if price_val < 1 or price_val > 50000:
                                        price = None
                                except:
                                    price = None
                        elif isinstance(offers, list) and len(offers) > 0:
                            price = offers[0].get("price")
                    
                    if title and price:
                        break
            except (json.JSONDecodeError, TypeError):
                continue
    except Exception as e:
        print(f"JSON-LD Extraction failed: {e}")

    # DISCARD if no specific price found (stealth precision)
    if not price or price == "Check Best Price":
        return None

    # DISCARD if no proper title (likely category page)
    if not title or len(title) < 3:
        return None
    
    # REVENUE TAG LOCK: Hard-code anany-21 at the scraper level
    if "?" in url:
        tagged_url = f"{url}&tag=anany-21"
    else:
        tagged_url = f"{url}?tag=anany-21"

    result = {
        "title": title,
        "price": price,
        "url": tagged_url
    }
    
    # Stock & Urgency Extraction
    # Patterns: "Only X left in stock", "X% claimed" on Lightning Deals
    text_lower = html.lower() # Use raw HTML for text search to be more thorough
    
    # Exact count left in stock
    m = re.search(r"only\s+(\d+)\s+left\s+in\s+stock", text_lower)
    if m:
        count = int(m.group(1))
        result["low_stock"] = True
        result["stock_count"] = count
    else:
        # Heuristic fallback: presence of phrases without number
        if "left in stock" in text_lower and "only" in text_lower:
            result["low_stock"] = True
            result["stock_count"] = 5
    
    # Percent claimed (Lightning Deal style)
    m2 = re.search(r"(\d{1,3})% claimed", text_lower)
    if m2:
        pc = int(m2.group(1))
        result["percent_claimed"] = pc
        # Infer low stock when available percentage is low
        if pc >= 80:
            result["low_stock"] = True
    
    # Append urgency tag
    try:
        tag = None
        is_loot = False
        
        # Check stock condition
        if result.get("low_stock") and result.get("stock_count") is not None and result["stock_count"] < 10:
            is_loot = True
            
        # Check discount condition (if we had it). 
        # Look for savings text like "-71%"
        savings_match = re.search(r"-(\d{1,2})%", text_lower)
        if savings_match:
            discount_pct = int(savings_match.group(1))
            result["discount_percent"] = discount_pct
            if discount_pct > 70:
                is_loot = True

        if is_loot:
            tag = "🚨 LOOT ALERT"
        elif result.get("percent_claimed") is not None and result["percent_claimed"] >= 80:
             tag = "[🔥 LOW STOCK – ~20% LEFT]"
             
        if tag:
            t = result["title"]
            if tag not in t:
                result["title"] = f"{tag} {t}"
    except Exception:
        pass
    
    return result
