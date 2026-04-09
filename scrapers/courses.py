import aiohttp
import asyncio
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

async def get_free_courses(url):
    """
    ATOMIC SCRAPING: Click into individual deals and parse Product Title and Direct Buy Link.
    Only process individual course/product pages, not category listings.
    """
    # ANTI-CATEGORY LOGIC: Only process individual product URLs
    from bot import is_individual_product_url
    if not is_individual_product_url(url):
        return []
    
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
    
    # ATOMIC SCRAPING: Look for individual course links, not category cards
    # This targets individual course pages directly
    course_links = soup.select("a[href*='/course/'], a[href*='/p/'], a[href*='/product/']")
    
    if not course_links:
        # Fallback: Look for course cards but will need to click through
        cards = soup.select(".card, .course-card, .course-listing, .udlite-search-course-card")
        for card in cards:
            link_elem = card.select_one("a[href]")
            if link_elem:
                course_links.append(link_elem)
    
    for link_elem in course_links:
        link = link_elem.get("href")
        
        if not link:
            continue
            
        # Fix relative links
        if link.startswith("/"):
            if "discudemy.com" in url:
                link = "https://www.discudemy.com" + link
            elif "couponami.net" in url:
                link = "https://www.couponami.net" + link
        
        # ANTI-CATEGORY: Ensure this is an individual course/product
        if not is_individual_product_url(link):
            continue
        
        # Extract title - prefer the link text itself (more reliable)
        title = link_elem.get_text(strip=True)
        if not title:
            # Fallback to card title
            title_elem = link_elem.select_one(".card-header, h3, .course-title")
            if title_elem:
                title = title_elem.get_text(strip=True)
        
        # Skip if no proper title (likely category/navigation)
        if not title or len(title) < 3 or "coupon" in title.lower() or "deal" in title.lower():
            continue
        
        # Format: "Brand + Model" - for courses, use "Platform + Course Name"
        if "udemy" in link.lower():
            title = f"Udemy {title}"
        elif "discudemy" in link.lower():
            title = f"Discudemy {title}"
        
        courses.append({
            "title": title,
            "url": link
        })

    return courses
