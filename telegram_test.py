import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_test_message():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: BOT_TOKEN or TELEGRAM_CHAT_ID missing in .env")
        return

    print(f"Testing Telegram Bot...")
    print(f"Token: {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}")
    print(f"Chat ID: {CHAT_ID}")

    bot = Bot(token=BOT_TOKEN)

    try:
        # Send a text message
        message = await bot.send_message(chat_id=CHAT_ID, text="🔔 Telegram Test: Connection Successful!")
        print(f"✅ Success! Message sent. Message ID: {message.message_id}")
    except TelegramError as e:
        print(f"❌ Failed to send message: {e}")

if __name__ == "__main__":
    asyncio.run(send_test_message())
