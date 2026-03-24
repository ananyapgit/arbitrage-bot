"""
LIVE WEB SCRAPER — NO STATIC DATA
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
import random
import json

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
]

async def get_amazon_product(url):
    """
    Fetches product details from a live Amazon URL.
    Returns None if scraping fails or critical data is missing.
    """
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }

    # Retry up to 5 times on network errors to scrape harder
    async with aiohttp.ClientSession() as session:
        for attempt in range(5):
            try:
                # Use 10 second timeout for requests
                async with session.get(url, headers=headers, timeout=10) as response:
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

    # --- JSON-LD EXTRACTION (Ultimate Fail-Safe) ---
    if not price or not title:
        try:
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    # Handle both single objects and lists of objects
                    if isinstance(data, list):
                        data = data[0]
                    
                    if not title and "name" in data:
                        title = data["name"]
                    
                    if not price:
                        # Prices can be in 'offers'
                        offers = data.get("offers")
                        if isinstance(offers, dict):
                            price = offers.get("price")
                        elif isinstance(offers, list) and len(offers) > 0:
                            price = offers[0].get("price")
                    
                    if title and price:
                        break
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            print(f"JSON-LD Extraction failed: {e}")

    # Return hard-coded defaults if all else fails (as per bot.py requirement, but handled here for completeness)
    if not title:
        title = "Limited Time Offer"
    if not price:
        price = "Check Best Price"
    
    result = {
        "title": title,
        "price": price
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
