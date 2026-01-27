import sys
import os
import asyncio
import aiohttp
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import config
    import bot
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import dependencies: {e}")
    sys.exit(1)

# Configure logging to suppress noisy output during validation
logging.basicConfig(level=logging.CRITICAL)

async def check_connectivity():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("FAIL: BOT_TOKEN not found in environment variables.")
        return False
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"PASS: Telegram API is reachable. Bot: {data.get('result', {}).get('username')}")
                    return True
                else:
                    print(f"FAIL: Telegram API returned {resp.status}")
                    return False
    except Exception as e:
        print(f"FAIL: Telegram API connection failed: {e}")
        return False

def check_affiliate_tags():
    tags = getattr(config, "AFFILIATE_TAGS", {})
    required = ["amazon.in", "flipkart.com"]
    missing = []
    
    for t in required:
        if t not in tags or not tags[t]:
            missing.append(t)
    
    if not missing:
        print("PASS: Affiliate tags defined for Amazon and Flipkart.")
        return True
    else:
        print(f"FAIL: Missing affiliate tags (values are empty) for: {missing}")
        return False

def check_paths():
    # Paths relative to project root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = ["click_logs.csv", "rejection_audit.log"]
    success = True
    
    for f in files:
        path = os.path.join(root_dir, f)
        try:
            # Try to open for appending (creates if not exists)
            with open(path, "a") as file:
                pass
            print(f"PASS: {f} is writable.")
        except Exception as e:
            print(f"FAIL: {f} is NOT writable: {e}")
            success = False
            
    return success

async def check_redirect_resolver():
    print("TESTing Redirect Resolver...")
    test_url = "https://www.amazon.in/dp/B000000000"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Mock the session.get to avoid actual network call if possible, 
            # but bot.add_affiliate_tag does a network call to resolve redirects.
            # For validation, we can let it fail gracefully on network or mock it.
            # But the requirement is "Verifies that the bot correctly appends the tag".
            # We will rely on the actual logic.
            
            # Since B000000000 might return 404, we just check if tag is appended to the URL string.
            # bot.add_affiliate_tag might fail redirect resolution but should still return URL.
            
            tagged_url = await bot.add_affiliate_tag(session, test_url, "amazon.in")
            
            expected_tag = config.AFFILIATE_TAGS.get("amazon.in")
            
            if expected_tag and expected_tag in tagged_url:
                print(f"PASS: Redirect Resolver appended tag correctly.\n      Input: {test_url}\n      Output: {tagged_url}")
                return True
            else:
                print(f"FAIL: Redirect Resolver failed to append tag.\n      Input: {test_url}\n      Output: {tagged_url}")
                return False
                
    except Exception as e:
        print(f"FAIL: Redirect Resolver threw exception: {e}")
        return False

async def main():
    print("\n🔥 LAUNCH VALIDATOR: PRE-FLIGHT CHECKLIST 🔥\n")
    
    results = []
    
    print("--- 1. Affiliate Tag Check ---")
    results.append(check_affiliate_tags())
    
    print("\n--- 2. Path Verification ---")
    results.append(check_paths())
    
    print("\n--- 3. Connectivity Check ---")
    results.append(await check_connectivity())
    
    print("\n--- 4. Redirect Resolver ---")
    results.append(await check_redirect_resolver())
    
    print("\n" + "="*30)
    if all(results):
        print("✅ SYSTEM 100% READY FOR DEPLOYMENT")
        print("="*30)
        # Create success report
        with open("launch_validation_report.json", "w") as f:
            f.write('{"status": "READY", "timestamp": "final"}')
    else:
        print("❌ SYSTEM NOT READY. FIX ERRORS ABOVE.")
        print("="*30)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
