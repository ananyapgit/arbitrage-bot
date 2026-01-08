import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

def get_amazon_product(url):
    # Retry up to 3 times on network errors
    for attempt in range(3):
        try:
            # Use 10 second timeout for requests
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            break  # Success, exit retry loop
        except requests.RequestException:
            if attempt == 2:  # Last attempt failed
                return None
            # Retry on network error
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    title = soup.select_one("#productTitle")
    price = soup.select_one(".a-price-whole")
    
    # Return None if title or price is missing
    if not title or not price:
        return None
    
    return {
        "title": title.get_text(strip=True),
        "price": price.get_text(strip=True)
    }
