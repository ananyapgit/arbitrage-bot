import asyncio
import logging
import csv
import os
from datetime import datetime
from aiohttp import web
import aiofiles

# Config
HOST = "0.0.0.0"
PORT = 8080
CLICK_LOG_FILE = "click_logs.csv"

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def log_click(data: dict):
    """
    Logs click metadata to CSV.
    Fail-Safe: Any error here must NOT bubble up to block the redirect.
    """
    try:
        file_exists = os.path.isfile(CLICK_LOG_FILE)
        async with aiofiles.open(CLICK_LOG_FILE, mode='a', newline='') as f:
            # We construct CSV line manually to avoid blocking CSV writer calls or complex async wrappers
            # Order: timestamp, user_id, category, platform, target_url
            timestamp = datetime.now().isoformat()
            row = f"{timestamp},{data.get('user_id','')},{data.get('category','')},{data.get('platform','')},{data.get('url','')}\n"
            
            if not file_exists:
                header = "timestamp,user_id,category,platform,target_url\n"
                await f.write(header)
            
            await f.write(row)
    except Exception as e:
        # FT-RI-01: Log failure must fail closed (log error, allow redirect)
        logging.error(f"Click Logging Failed: {e}")

async def redirect_handler(request):
    """
    Handles redirect requests.
    Query Params: url (required), user_id, category, platform
    """
    start_time = datetime.now()
    
    # 1. Extract Parameters
    params = request.query
    target_url = params.get("url")
    
    if not target_url:
        return web.Response(text="Missing 'url' parameter", status=400)

    # 2. Log Click (Non-blocking / Fire-and-Forget intent)
    log_data = {
        "url": target_url,
        "user_id": params.get("user_id", "anonymous"),
        "category": params.get("category", "general"),
        "platform": params.get("platform", "web")
    }

    # FT-RI-02: Redirect Downtime/Timeout resilience.
    # We wrap logging in a timeout to ensure we never block the user for > 200ms even if disk/DB is slow.
    try:
        await asyncio.wait_for(log_click(log_data), timeout=0.2)
    except asyncio.TimeoutError:
        logging.error(f"Click Logging Timeout for {target_url} - Proceeding with redirect")
    except Exception as e:
        logging.error(f"Click Logging Error: {e}")
    
    # 3. Issue Redirect
    return web.HTTPFound(target_url)

async def health_check(request):
    return web.Response(text="OK")

def create_app():
    app = web.Application()
    app.add_routes([
        web.get('/r', redirect_handler),
        web.get('/health', health_check)
    ])
    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host=HOST, port=PORT)
