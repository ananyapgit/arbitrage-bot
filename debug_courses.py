import aiohttp
import asyncio

async def fetch_html():
    url = "https://www.discudemy.com/all"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            print(f"Status: {response.status}")
            html = await response.text()
            with open("debug_courses.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved HTML to debug_courses.html")

if __name__ == "__main__":
    asyncio.run(fetch_html())
