import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

async def get_amazon_product(url):
    # Retry up to 3 times on network errors
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                # Use 10 second timeout for requests
                async with session.get(url, headers=HEADERS, timeout=10) as response:
                    response.raise_for_status()
                    html = await response.text()
                    break  # Success, exit retry loop
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == 2:  # Last attempt failed
                    return None
                # Retry on network error
    
    soup = BeautifulSoup(html, "html.parser")
    
    title = soup.select_one("#productTitle")
    price = soup.select_one(".a-price-whole")
    
    # Return None if title or price is missing
    if not title or not price:
        return None
    
    result = {
        "title": title.get_text(strip=True),
        "price": price.get_text(strip=True)
    }
    
    # Stock & Urgency Extraction
    # Patterns: "Only X left in stock", "X% claimed" on Lightning Deals
    text_lower = soup.get_text(" ", strip=True).lower()
    
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
    
    # Append urgency tag once if low stock
    try:
        tag = None
        if result.get("low_stock") and result.get("stock_count") is not None and result["stock_count"] < 10:
            tag = f"[🔥 LOW STOCK – {result['stock_count']} LEFT]"
        elif result.get("percent_claimed") is not None and result["percent_claimed"] >= 80:
            # Approximate: if 80% claimed, ~20% left
            tag = "[🔥 LOW STOCK – ~20% LEFT]"
        if tag:
            t = result["title"]
            if tag not in t:
                result["title"] = f"{t} {tag}"
    except Exception:
        pass
    
    return result
