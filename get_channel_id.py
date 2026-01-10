from telegram import Bot
import asyncio

bot = Bot(token="8529561535:AAGH88AnbX7G6xepaDh4a7tC-IWyg35YbN0")

async def get_id():
    updates = await bot.get_updates()
    for u in updates:
        print(u)

asyncio.run(get_id())
