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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

def get_manual_fallback_url(url: str) -> str:
    """Manual URL Constructor fallback for EarnKaro 403 scenarios."""
    if "amazon.in" in url:
        return f"https://earnkaro.com/api/v1/generate_link?url={url}"
    return url

SEED_URLS = [
    "https://earnkaro.com/",
    "https://earnkaro.com/stores",
    "https://earnkaro.com/stores/amazon-india-offers",
    "https://earnkaro.com/stores/flipkart-offers",
    "https://earnkaro.com/stores/myntra-offers",
    "https://earnkaro.com/stores/ajio-offers",
    "https://earnkaro.com/stores/tata-cliq-offers",
    "https://earnkaro.com/stores/mamaearth-offers",
    "https://earnkaro.com/stores/wow-skin-science-offers",
    "https://earnkaro.com/stores/beardo-offers"
]

def _clean(text: str) -> str:
    return " ".join((text or "").split()).strip()[:280]

async def get_earnkaro_deals(limit: int = 20) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()

    def get_headers():
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.google.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
        }

    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            for base in SEED_URLS:
                try:
                    # Random delay to avoid 403
                    await asyncio.sleep(random.uniform(2, 5))
                    async with session.get(base, headers=get_headers(), timeout=20) as resp:
                        if resp.status == 403:
                            logging.warning(f"EarnKaro 403 Forbidden for {base} - possibly bot-detected")
                            continue
                        if resp.status != 200:
                            logging.warning(f"EarnKaro failed with status {resp.status} for {base}")
                            continue
                        html_content = await resp.text()
                    
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # Log the page title to verify we got the right page
                    pg_title = soup.title.string if soup.title else "No Title"
                    logging.info(f"Scraping {base} - Title: {pg_title}")

                    # 1. Try to find JSON data in __NEXT_DATA__ (common for Next.js sites like EarnKaro)
                    next_data = soup.find("script", id="__NEXT_DATA__")
                    if next_data:
                        try:
                            import json
                            data = json.loads(next_data.string)
                            
                            # Log structure for debugging
                            props = data.get('props', {})
                            page_props = props.get('pageProps', {})
                            if 'welcomepage' in page_props:
                                logging.warning(f"EarnKaro returned 'welcomepage' for {base}. We might be blocked or need a session.")
                            
                            logging.info(f"__NEXT_DATA__ keys: {list(data.keys())}")
                            logging.info(f"Props keys: {list(props.keys())}")
                            logging.info(f"PageProps keys: {list(page_props.keys())}")
                            
                            def find_deals_in_json(obj, depth=0):
                                found = []
                                if depth > 20: return found # Increased depth
                                if isinstance(obj, dict):
                                    # Look for keys used by EarnKaro
                                    # title, productName, name, brandName
                                    # url, profitLink, link, targetUrl
                                    title = obj.get("title") or obj.get("productName") or obj.get("name") or obj.get("brandName")
                                    url = obj.get("url") or obj.get("profitLink") or obj.get("link") or obj.get("targetUrl")
                                    
                                    # EarnKaro specific: sometimes deals are in 'deals' or 'offers' arrays
                                    if title and url and isinstance(url, str) and ("http" in url or url.startswith("/")):
                                        # Ensure it's not just a menu link
                                        url_low = url.lower()
                                        if any(x in url_low for x in ["/p/", "/deal/", "/offer/", "/profit-link/", "profitLink"]):
                                            found.append({
                                                "title": str(title),
                                                "url": url,
                                                "source": "earnkaro",
                                                "marketplace": "EarnKaro"
                                            })
                                    
                                    for k, v in obj.items():
                                        # Optimization: skip known large non-deal branches if needed
                                        if k in ['menu', 'header', 'footer', 'seo']: continue
                                        found.extend(find_deals_in_json(v, depth + 1))
                                elif isinstance(obj, list):
                                    for item in obj:
                                        found.extend(find_deals_in_json(item, depth + 1))
                                return found
                            
                            json_deals = find_deals_in_json(data)
                            # Fallback: Scrape links from HTML if JSON is empty
                            if not json_deals:
                                logging.info(f"JSON yielded 0 deals for {base}, trying HTML extraction...")
                                for a in soup.find_all("a", href=True):
                                    href = a['href']
                                    text = a.get_text(strip=True)
                                    # Look for profit links or product-like links
                                    if any(x in href.lower() for x in ["/p/", "/deal/", "/offer/", "profitlink", "targeturl"]):
                                        if len(text) > 10: # Likely a product title
                                            json_deals.append({
                                                "title": text,
                                                "url": href,
                                                "source": "earnkaro",
                                                "marketplace": "EarnKaro"
                                            })
                            
                            logging.info(f"Found {len(json_deals)} candidate deals for {base}")
                            for d in json_deals:
                                if d["title"] and d["url"] and d["url"] not in seen:
                                    seen.add(d["url"])
                                    out.append(d)
                                    if len(out) >= limit: return out
                        except Exception as e:
                            logging.warning(f"Failed to parse __NEXT_DATA__ for {base}: {e}")

                    # 2. Fallback: Be more aggressive in finding links
                    all_links = soup.find_all("a", href=True)
                    logging.info(f"Total links found on {base}: {len(all_links)}")
                    
                    for a in all_links:
                        href = (a.get("href") or "").strip()
                        if not href or "#" in href or "javascript:" in href:
                            continue
                        
                        url = urljoin(base, href)
                        if url in seen:
                            continue
                        
                        url_low = url.lower()
                        # Look for anything that looks like a deal or profit link
                        # EarnKaro links often look like earnkaro.com/p/123 or earnkaro.com/deal/abc
                        is_likely_deal = any(x in url_low for x in ["/p/", "/deal/", "/offer/", "/profit-link/", "profitLink"])
                        
                        if not is_likely_deal:
                            # Also check if it's a store link that might lead to deals
                            if "/stores/" in url_low and url_low != base.lower():
                                is_likely_deal = True
                        
                        if not is_likely_deal:
                            continue

                        txt = _clean(a.get_text(" ", strip=True))
                        # Try harder to find a title
                        if not txt or len(txt) < 4:
                            # Look at title or aria-label
                            txt = _clean(a.get("title") or a.get("aria-label") or "")
                        
                        if not txt or len(txt) < 4:
                            # Look at parent's text
                            p = a.parent
                            if p:
                                txt = _clean(p.get_text(" ", strip=True))
                        
                        if not txt or len(txt) < 4:
                            # Look for img alt
                            img = a.find("img", alt=True)
                            if img:
                                txt = _clean(img["alt"])

                        if not txt or len(txt) < 4:
                            # Use the last part of URL as title if desperate
                            txt = url.split("/")[-1].replace("-", " ").capitalize()

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
