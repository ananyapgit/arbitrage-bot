import aiohttp
import asyncio
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

async def get_free_courses(url):
    html = None
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(3):
            try:
                async with session.get(url, headers=HEADERS, timeout=10) as response:
                    response.raise_for_status()
                    html = await response.text()
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == 2:
                    return []
    
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    courses = []
    cards = soup.select(".course-card, .course-listing, .udlite-search-course-card")

    for card in cards:
        title = card.select_one("h3, .course-title")
        link = card.select_one("a")

        if not title or not link:
            continue

        courses.append({
            "title": title.get_text(strip=True),
            "url": link.get("href")
        })

    return courses
