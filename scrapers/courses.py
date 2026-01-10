import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

def get_free_courses(url):
    response = None

    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 2:
                return []

    soup = BeautifulSoup(response.text, "html.parser")

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
