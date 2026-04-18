"""
LIVE FLIPKART SCRAPER
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import random
import config

USER_AGENTS = [
    # Desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Mobile
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-A536E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]


async def get_flipkart_deals(limit: int = 20) -> list[dict]:
    """
    Lightweight Flipkart candidate scraper (best-effort).
    Extracts product links from a public listing page so the pipeline touches Flipkart each run.
    """
    # Mobile search endpoint pattern (mweb headers reduce bot friction)
    urls = [
        "https://www.flipkart.com/search?q=electronics&marketplace=FLIPKART",
        "https://www.flipkart.com/search?q=smartphone%20deal&marketplace=FLIPKART",
    ]
    mobile_ua = random.choice([ua for ua in USER_AGENTS if "Mobile" in ua or "Android" in ua or "iPhone" in ua] or USER_AGENTS)
    headers = {
        "User-Agent": mobile_ua,
        "x-user-agent": mobile_ua,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    out: list[dict] = []
    seen: set[str] = set()

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for u in urls:
            try:
                async with session.get(u, headers=headers, timeout=config.REQUEST_TIMEOUT) as resp:
                    if resp.status != 200:
                        continue
                    html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select("a[href*='/p/']"):
                    href = (a.get("href") or "").strip()
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = "https://www.flipkart.com" + href.split("?")[0]
                    if "/p/" not in href or href in seen:
                        continue
                    title = a.get("title") or a.get_text(" ", strip=True)
                    if not title or len(title) < 4:
                        continue
                    seen.add(href)
                    out.append({"title": title[:220], "url": href, "source": "flipkart", "marketplace": "Flipkart"})
                    if len(out) >= limit:
                        return out
            except Exception:
                continue
    return out

async def get_flipkart_product(url):
    """
    Fetches product details from a live Flipkart URL.
    """
    # ANTI-CATEGORY LOGIC: Only process individual product URLs
    from bot import is_individual_product_url
    if not is_individual_product_url(url):
        return None
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }

    async with aiohttp.ClientSession() as session:
        for attempt in range(5):
            try:
                # Use optimized timeout from config
                async with session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT) as response:
                    if response.status != 200:
                        continue # Try again on non-200 status
                    html = await response.text()
                    break # Success
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == 4:
                    return None # All retries failed
                await asyncio.sleep(random.uniform(1, 3))
        else: # Loop finished without break (all retries failed)
            return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Heuristic Selectors for Flipkart
    title = soup.select_one(".B_NuCI") # Common title class
    if not title:
        title = soup.select_one("h1")
        
    price = soup.select_one("._30jeq3._16Jk6d") # Common price class
    if not price:
        price = soup.select_one("._30jeq3")

    # --- BUYABILITY VALIDATION ---
    text_lower = html.lower()
    buy_markers = [
        "add to cart", "buy now", "proceed to buy", 
        "add_to_cart", "buy_now"
    ]
    has_buy_button = any(marker in text_lower for marker in buy_markers)
    if not has_buy_button:
        return None

    if not title:
        return None
    
    # REVENUE TAG LOCK: Hard-code affid=anany at the scraper level
    sep = "&" if "?" in url else "?"
    tagged_url = f"{url}{sep}affid=anany"
    
    return {
        "title": title.get_text(strip=True),
        "price": price.get_text(strip=True) if price else "N/A",
        "url": tagged_url,
        "marketplace": "Flipkart"
    }
