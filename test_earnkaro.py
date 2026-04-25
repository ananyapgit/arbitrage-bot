
import asyncio
import logging
from scrapers.earnkaro import get_earnkaro_deals

async def test_earnkaro():
    logging.basicConfig(level=logging.INFO)
    print("Testing EarnKaro scraper...")
    deals = await get_earnkaro_deals(limit=5)
    print(f"Found {len(deals)} deals")
    for i, d in enumerate(deals):
        print(f"{i+1}. {d['title']} ({d['url']})")
    
    if not deals:
        print("No deals found. The scraper might need adjustment for the current page structure.")

if __name__ == "__main__":
    asyncio.run(test_earnkaro())
