import asyncio
from scrapers.courses import get_free_courses

async def main():
    deals = await get_free_courses("https://www.discudemy.com/all")
    print(f"Found {len(deals)} deals")
    if deals:
        print("Sample deal:", deals[0])

if __name__ == "__main__":
    asyncio.run(main())
