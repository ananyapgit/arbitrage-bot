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
    # Updated selectors for Discudemy/Couponami
    cards = soup.select(".card, .course-card, .course-listing, .udlite-search-course-card")

    for card in cards:
        # Title/Link selector
        title_elem = card.select_one(".card-header, h3, .course-title")
        link_elem = card.select_one(".card-header, a")

        if not title_elem or not link_elem:
            continue

        title = title_elem.get_text(strip=True)
        link = link_elem.get("href")
        
        if not link:
            continue
            
        # Fix relative links if any (though source seems absolute)
        if link.startswith("/"):
            link = "https://www.discudemy.com" + link

        courses.append({
            "title": title,
            "url": link
        })

    return courses
