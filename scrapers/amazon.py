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
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Category rotation for diverse scraping
AMAZON_CATEGORIES = [
    "electronics", "home-kitchen", "fashion", "beauty", "toys", "sports", "books"
]

# UA Shield: rotate 5+ mobile/desktop UAs
USER_AGENTS = [
    # Desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Mobile
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-A536E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]


def _force_affiliate(url: str) -> str:
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["tag"] = config.AFFILIATE_TAGS.get("amazon.in") or "anany-21"
    return urlunparse(parsed._replace(query=urlencode(params)))


def _extract_listing_deals(soup: BeautifulSoup) -> list[dict]:
    deals: list[dict] = []
    seen: set[str] = set()

    for anchor in soup.select("a[href*='/dp/']"):
        href = anchor.get("href", "").strip()
        if not href:
            continue
        if href.startswith("/"):
            href = "https://www.amazon.in" + href.split("?")[0]
        if "/dp/" not in href or href in seen:
            continue

        container = anchor.parent
        title = (
            anchor.get("title")
            or anchor.get_text(" ", strip=True)
            or (anchor.select_one("img[alt]") or {}).get("alt")
        )
        price_el = None
        if container and hasattr(container, "select_one"):
            price_el = container.select_one(".a-price .a-offscreen, .a-price-whole, .a-offscreen")
        price = price_el.get_text(strip=True) if price_el else None

        if title:
            seen.add(href)
            deals.append(
                {
                    "title": title.strip(),
                    "url": href,
                    "affiliate_url": _force_affiliate(href),
                    "price": price,
                    "discount": None,
                    "source": "amazon",
                    "marketplace": "Amazon",
                }
            )

    return deals

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
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
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
                                        purl = item.get("url")
                                        if purl and isinstance(purl, str) and purl.startswith("/"):
                                            purl = "https://www.amazon.in" + purl
                                        product = {
                                            "title": item.get("name"),
                                            "url": purl,
                                            "affiliate_url": _force_affiliate(purl) if purl else None,
                                            "price": item.get("offers", {}).get("price"),
                                            "discount": None,
                                            "source": "amazon",
                                            "marketplace": "Amazon"
                                        }
                                        if product["title"] and product["url"] and product.get("affiliate_url"):
                                            deals.append(product)
                        except:
                            continue
                    
                    deals.extend(_extract_listing_deals(soup))
                    return deals
                return []
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
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # SEO Pivot: parse JSON-LD (avoid CSS selectors for price)
                    deals = []
                    try:
                        for script in soup.find_all("script", type="application/ld+json"):
                            try:
                                data = json.loads(script.string)
                            except Exception:
                                continue
                            objs = data if isinstance(data, list) else [data]
                            for obj in objs:
                                if not isinstance(obj, dict):
                                    continue
                                if obj.get("@type") == "ItemList":
                                    items = obj.get("itemListElement") or []
                                    for it in items:
                                        if not isinstance(it, dict):
                                            continue
                                        prod = it.get("item") if isinstance(it.get("item"), dict) else it
                                        if not isinstance(prod, dict):
                                            continue
                                        if prod.get("@type") != "Product":
                                            continue
                                        title = str(prod.get("name") or "").strip()
                                        purl = prod.get("url")
                                        if purl and isinstance(purl, str) and purl.startswith("/"):
                                            purl = "https://www.amazon.in" + purl
                                        offers = prod.get("offers") if isinstance(prod.get("offers"), (dict, list)) else None
                                        price = None
                                        old_price = None
                                        if isinstance(offers, dict):
                                            price = offers.get("price")
                                        elif isinstance(offers, list) and offers and isinstance(offers[0], dict):
                                            price = offers[0].get("price")
                                        if title and purl and price is not None:
                                            deals.append(
                                                {
                                                    "title": title,
                                                    "url": purl,
                                                    "affiliate_url": _force_affiliate(purl),
                                                    "price": price,
                                                    "old_price": old_price,
                                                    "discount": None,
                                                    "source": "amazon",
                                                    "marketplace": "Amazon",
                                                }
                                            )
                    except Exception:
                        pass
                    
                    deals.extend(_extract_listing_deals(soup))
                    return deals
                return []
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
        movers_deals = await get_amazon_movers_shakers() or []
        all_deals.extend(movers_deals)
    except Exception as e:
        print(f"Movers & Shakers failed: {e}")
    
    # Try Today's Deals as fallback
    try:
        today_deals = await get_amazon_todays_deals() or []
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
        print(f"Amazon rejected non-product URL: {url}")
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
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for attempt in range(5):
            try:
                # Use optimized timeout from config
                async with session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT) as response:
                    if response.status in (403, 429, 503):
                        with open("health_check.log", "a") as f:
                            f.write(f"{datetime.now()}: Amazon blocked for {url} ({response.status})\n")
                        print(f"Amazon blocked: {url}")
                        return None
                    response.raise_for_status()
                    html = await response.text()
                    text_lower = html.lower()
                    if any(marker in text_lower for marker in [
                        "captcha",
                        "enter the characters you see below",
                        "sorry, we just need to make sure you're not a robot",
                        "robot check",
                    ]):
                        with open("health_check.log", "a") as f:
                            f.write(f"{datetime.now()}: Amazon blocked for {url} (captcha)\n")
                        print(f"Amazon blocked: {url}")
                        return None
                    break  # Success, exit retry loop
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == 2:  # Last attempt failed
                    return None
                await asyncio.sleep(random.uniform(1, 3)) # Add jitter between retries
    
    soup = BeautifulSoup(html, "html.parser")

    # MACHINE-DATA PARSING (SEO Pivot):
    # - Primary: JSON-LD Product -> offers.price + offers.priceCurrency
    # - Fallback: meta[property='og:price:amount'|'product:price:amount'] (+ currency tags)
    title = None
    price = None
    currency = None
    product_id = None
    try:
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                # Handle both single objects and lists of objects
                objs = data if isinstance(data, list) else [data]
                for obj in objs:
                    if not isinstance(obj, dict):
                        continue
                    if obj.get("@type") != "Product":
                        continue
                    if not title and obj.get("name"):
                        title = str(obj.get("name")).strip()
                    if not product_id:
                        product_id = obj.get("sku") or obj.get("productID") or obj.get("mpn")
                    offers = obj.get("offers")
                    if isinstance(offers, dict):
                        if price is None:
                            price = offers.get("price")
                        if currency is None:
                            currency = offers.get("priceCurrency")
                    elif isinstance(offers, list) and offers:
                        o0 = offers[0] if isinstance(offers[0], dict) else {}
                        if price is None:
                            price = o0.get("price")
                        if currency is None:
                            currency = o0.get("priceCurrency")
                    if title and price:
                        break
                if title and price:
                    break
            except (json.JSONDecodeError, TypeError):
                continue
    except Exception as e:
        print(f"JSON-LD Extraction failed: {e}")

    # Metadata fallback (no CSS selectors)
    if not title:
        meta_title = soup.find("meta", attrs={"property": "og:title"}) or soup.find("meta", attrs={"name": "title"})
        title = meta_title.get("content", "").strip() if meta_title else None

    if not price:
        price_meta = soup.find("meta", attrs={"property": "product:price:amount"}) or soup.find(
            "meta", attrs={"property": "og:price:amount"}
        )
        price = price_meta.get("content", "").strip() if price_meta else None
    if not currency:
        cur_meta = soup.find("meta", attrs={"property": "product:price:currency"}) or soup.find(
            "meta", attrs={"property": "og:price:currency"}
        )
        currency = cur_meta.get("content", "").strip() if cur_meta else None

    # DISCARD if no specific price found (stealth precision)
    if not price:
        print(f"Amazon missing price: {url}")
        return None

    # DISCARD if no proper title (likely category page)
    if not title or len(title) < 3:
        print(f"Amazon missing title: {url}")
        return None
    
    # REVENUE TAG LOCK: preserve query params while forcing the affiliate tag
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["tag"] = config.AFFILIATE_TAGS.get("amazon.in") or "anany-21"
    tagged_url = urlunparse(parsed._replace(query=urlencode(params)))

    result = {
        "title": title,
        "price": price,
        "url": url,
        "affiliate_url": tagged_url,
        "source": "amazon",
        "marketplace": "Amazon"
    }

    try:
        cur = currency or "INR"
        print(f"[PRICE:FOUND] amazon price={price} currency={cur}", flush=True)
        result["price_currency"] = cur
    except Exception:
        pass
    
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
