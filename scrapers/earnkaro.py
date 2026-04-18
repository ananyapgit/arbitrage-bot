"""
Best-effort EarnKaro deal scraper.
Targets public EarnKaro deals pages to pull candidate profit links.
Any failure must return [] (never crash the bot).
"""

from __future__ import annotations

import asyncio
import logging
import random
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup


USER_AGENTS = [
    # Desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    # Mobile
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]


SEED_URLS = [
    "https://earnkaro.com/deals",
    "https://earnkaro.com/offers",
    "https://earnkaro.com/stores/amazon-india-offers",
    "https://earnkaro.com/stores/flipkart-offers",
    "https://earnkaro.com/stores/myntra-offers"
]


def _clean(text: str) -> str:
    return " ".join((text or "").split()).strip()[:280]


async def get_earnkaro_deals(limit: int = 20) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            for base in SEED_URLS:
                try:
                    async with session.get(base, headers={**headers, "User-Agent": random.choice(USER_AGENTS)}, timeout=20) as resp:
                        if resp.status != 200:
                            continue
                        html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    # Broader link extraction for EarnKaro
                    for a in soup.find_all("a", href=True):
                        href = (a.get("href") or "").strip()
                        if not href or "#" in href:
                            continue
                        url = urljoin(base, href)
                        if url in seen:
                            continue
                        
                        txt = _clean(a.get_text(" ", strip=True))
                        # If title is empty, try to find one in siblings or parent
                        if not txt or len(txt) < 4:
                            parent = a.parent
                            if parent:
                                txt = _clean(parent.get_text(" ", strip=True))
                        
                        if not txt or len(txt) < 6:
                            continue
                        
                        # Target profit-link redirects or store links
                        url_low = url.lower()
                        if "earnkaro.com" not in url_low:
                            continue
                        
                        is_deal = any(x in url_low for x in ["/deal", "/offer", "/store", "/p/", "/product"])
                        if not is_deal:
                            continue

                        seen.add(url)
                        out.append(
                            {
                                "title": txt,
                                "url": url,
                                "affiliate_url": url,
                                "source": "earnkaro",
                                "marketplace": "EarnKaro",
                            }
                        )
                        if len(out) >= limit:
                            return out
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    logging.warning("EarnKaro scraper failed (%s): %s", base, exc)
                    continue
    except Exception as exc:
        logging.warning("EarnKaro scraper session failed: %s", exc)
        return []

    return out

