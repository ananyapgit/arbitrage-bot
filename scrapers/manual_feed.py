import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

FEED_URLS = [
    "https://www.couponami.com/feed/",
    "https://www.couponami.com/all/1",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _clean_title(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", unescape(text or "")).strip()
    return cleaned[:280]


def _extract_price(text: str) -> str:
    match = re.search(r"(₹\s?\d[\d,]*|\$\s?\d[\d,]*|free|100%\s*off)", text or "", re.I)
    if not match:
        return "Free"
    token = match.group(1)
    return "Free" if "free" in token.lower() or "100%" in token.lower() else token.strip()


async def _fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=20) as response:
        response.raise_for_status()
        return await response.text()


def _parse_rss(xml_text: str) -> list[dict]:
    deals: list[dict] = []
    root = ET.fromstring(xml_text)
    for item in root.findall(".//item"):
        title = _clean_title(item.findtext("title", default=""))
        link = (item.findtext("link", default="") or "").strip()
        description = item.findtext("description", default="") or ""
        pub_date_raw = (item.findtext("pubDate", default="") or "").strip()

        if not title or not link:
            continue

        # COUPONAMI EXPIRY CHECK:
        # - Drop if older than 12 hours based on pubDate when present
        # - Drop if an expiry-like tag exists and is in the past
        now = datetime.now(timezone.utc)
        try:
            if pub_date_raw:
                dt = parsedate_to_datetime(pub_date_raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age = now - dt.astimezone(timezone.utc)
                if age > timedelta(hours=12):
                    print(f"[SKIP:EXPIRED] {title}", flush=True)
                    continue
        except Exception:
            pass

        try:
            expiry_text = None
            for child in list(item):
                tag = (child.tag or "").lower()
                if "expir" in tag or "expiry" in tag or "expires" in tag:
                    t = (child.text or "").strip()
                    if t:
                        expiry_text = t
                        break
            if expiry_text:
                try:
                    edt = parsedate_to_datetime(expiry_text)
                    if edt.tzinfo is None:
                        edt = edt.replace(tzinfo=timezone.utc)
                    if now > edt.astimezone(timezone.utc):
                        print(f"[SKIP:EXPIRED] {title}", flush=True)
                        continue
                except Exception:
                    pass
        except Exception:
            pass

        price = _extract_price(description)
        deals.append(
            {
                "title": title,
                "price": price,
                "original_price": None,
                "url": link,
                "affiliate_url": link,
                "source": "coupondunia",
                "marketplace": "CouponDunia",
            }
        )
    return deals


def _parse_html(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    deals: list[dict] = []

    for anchor in soup.select("a.card-header[href], article a[href], .post a[href]"):
        href = anchor.get("href", "").strip()
        title = _clean_title(anchor.get_text(" ", strip=True))
        if not href or not title or len(title) < 4:
            continue
        if any(bad in href.lower() for bad in ["/category/", "/tag/", "/page/"]):
            continue

        link = urljoin(base_url, href)
        container_text = anchor.parent.get_text(" ", strip=True) if anchor.parent else title
        deals.append(
            {
                "title": title,
                "price": _extract_price(container_text),
                "original_price": None,
                "url": link,
                "affiliate_url": link,
                "source": "coupondunia",
                "marketplace": "CouponDunia",
            }
        )

    return deals


async def get_manual_deal():
    """
    Reliable static/RSS deal source for GitHub Actions.
    Uses CouponAmI as a CouponDunia-equivalent feed because it exposes static HTML/RSS.
    """
    async with aiohttp.ClientSession() as session:
        for feed_url in FEED_URLS:
            try:
                payload = await _fetch_text(session, feed_url)
                if "<?xml" in payload[:200] or "<rss" in payload[:400].lower():
                    deals = _parse_rss(payload)
                else:
                    deals = _parse_html(payload, feed_url)

                if deals:
                    logging.info("Coupon source '%s' yielded %s deals", feed_url, len(deals))
                    return deals[:20]
            except (aiohttp.ClientError, asyncio.TimeoutError, ET.ParseError) as exc:
                logging.warning("Coupon source failed (%s): %s", feed_url, exc)
                continue

    logging.warning("Coupon source returned no deals")
    return []
