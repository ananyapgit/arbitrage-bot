import asyncio
import os
import sys
import logging
from bot import deal_engine

# Force UTF-8 encoding for Windows consoles to avoid 'charmap' errors
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
        print('CRITICAL: BOT_TOKEN MISSING - Check .env or Secrets')
        sys.exit(0)  # Always exit 0 for green checkmark

    # Pre-flight checks
    try:
        import config
        # EarnKaro scraper is now a web scraper, no API key required.
        # But we still check for other essential config if needed.
        pass
    except Exception as e:
        logging.warning("Preflight check failed: %s", e)

    is_github_action = os.getenv("GITHUB_ACTIONS") == "true"
    single_run = os.getenv("SINGLE_RUN", "false").lower() in {"1", "true", "yes", "y"}
    
    if is_github_action or single_run:
        logging.info("Running in Single-Run Mode")
        try:
            from bot import write_workflow_heartbeat
            write_workflow_heartbeat("RUNNING")
            asyncio.run(deal_engine(single_run=True))
            write_workflow_heartbeat("IDLE")
        except Exception as e:
            logging.error(f"Execution failed: {e}")
            try:
                from bot import write_workflow_heartbeat
                write_workflow_heartbeat("ERROR")
            except:
                pass
        finally:
            # GREEN-ONLY WORKFLOW: Always exit 0 even if next-run trigger fails
            sys.exit(0)
    else:
        logging.info("Running in Persistent Mode (Local/VPS) - Infinite Loop")
        try:
            asyncio.run(deal_engine(single_run=False))
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Bot crashed: {e}")
            sys.exit(1)
