"""
LIVE FLIPKART SCRAPER
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import random
import config

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15"
]

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
