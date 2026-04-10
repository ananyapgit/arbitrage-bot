import asyncio
import os
import logging
from bot import deal_engine

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if __name__ == "__main__":
    # 4. PRE-FLIGHT CHECK (Hijack Safe)
    print("Checking Environment...")
    if not os.getenv('BOT_TOKEN'):
        import sys
        sys.exit('CRITICAL: BOT_TOKEN MISSING - Check .env or Secrets')

    is_github_action = os.getenv("GITHUB_ACTIONS") == "true"
    single_run = os.getenv("SINGLE_RUN", "false").lower() in {"1", "true", "yes", "y"}
    
    if is_github_action or single_run:
        logging.info("Running in Single-Run Mode")
        try:
            asyncio.run(deal_engine(single_run=True))
        except Exception as e:
            logging.error(f"Execution failed: {e}")
            exit(1)
    else:
        logging.info("Running in Persistent Mode (Local/VPS) - Infinite Loop")
        try:
            asyncio.run(deal_engine(single_run=False))
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
        except Exception as e:
            logging.error(f"Bot crashed: {e}")
            exit(1)
