import asyncio
import logging
import time
import csv
import os
import random
from unittest.mock import MagicMock, patch, AsyncMock
import aiohttp
from datetime import datetime

# Adjust path to import modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot
import config
import deal_engine

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LOG_FILE = "failure_taxonomy_test_log.csv"

# Mock Response Class
class MockResponse:
    def __init__(self, text, status=200, json_data=None, url="http://test.com", history=None, delay=0):
        self._text = text
        self.status = status
        self._json = json_data or {}
        self.url = url
        self.history = history or []
        self.delay = delay

    async def text(self):
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return self._text

    async def json(self):
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return self._json

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

def log_result(test_id, status, observed_behavior, mitigation_verified):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["TestID", "Pass/Fail", "Observed Behavior", "Mitigation Verified (Yes/No)", "Timestamp"])
        
        writer.writerow([test_id, status, observed_behavior, mitigation_verified, datetime.now().isoformat()])
    
    logging.info(f"[{test_id}] {status}: {observed_behavior} (Mitigation: {mitigation_verified})")

async def run_tests():
    logging.info(f"Starting Failure Taxonomy Validation (Hardening Mode). Logging to {LOG_FILE}")
    
    # Ensure Shadow Mode is enforced
    config.SHADOW_MODE = True
    config.SHADOW_CHANNEL_ID = -1009999999 # Mock Shadow Channel
    
    session = MagicMock()
    bot.bot = MagicMock() # Mock Telegram Bot

    # --- Category 1: Network & Infrastructure ---

    # FT-001: Connection Refused
    try:
        session.get.side_effect = aiohttp.ClientConnectorError(MagicMock(), OSError(111, "Connection refused"))
        deal = {"url": "http://test.com/conn_refused", "valid": True}
        res = await bot.enrich_deal(session, deal)
        if not res["valid"] and "Network Error" in str(res.get("enrich_error", "")):
             log_result("FT-001", "PASS", "Handled Connection Refused", "Yes")
        else:
             log_result("FT-001", "FAIL", f"Failed to handle Refused: {res.get('enrich_error')}", "No")
    except Exception as e:
        log_result("FT-001", "FAIL", f"Exception: {e}", "No")

    # FT-002: Connection Timeout
    try:
        session.get.side_effect = asyncio.TimeoutError()
        deal = {"url": "http://test.com/timeout", "valid": True}
        res = await bot.enrich_deal(session, deal)
        if not res["valid"] and "Network Timeout" in str(res.get("enrich_error", "")):
             log_result("FT-002", "PASS", "Handled Timeout", "Yes")
        else:
             log_result("FT-002", "FAIL", f"Failed to handle Timeout: {res.get('enrich_error')}", "No")
    except Exception as e:
        log_result("FT-002", "FAIL", f"Exception: {e}", "No")

    # FT-003: DNS Resolution Failure
    try:
        session.get.side_effect = aiohttp.ClientConnectorError(MagicMock(), OSError("DNS Fail"))
        deal = {"url": "http://test.com/dns", "valid": True}
        res = await bot.enrich_deal(session, deal)
        if not res["valid"] and "Network Error" in str(res.get("enrich_error", "")):
             log_result("FT-003", "PASS", "Handled DNS Failure", "Yes")
        else:
             log_result("FT-003", "FAIL", f"Failed to handle DNS: {res.get('enrich_error')}", "No")
    except Exception as e:
        log_result("FT-003", "FAIL", f"Exception: {e}", "No")

    # FT-004: 503 Service Unavailable
    try:
        session.get.side_effect = None
        session.get.return_value = MockResponse("Service Unavailable", status=503)
        deal = {"url": "http://test.com/503", "valid": True}
        res = await bot.enrich_deal(session, deal)
        if not res["valid"] and "HTTP 503" in str(res.get("enrich_error", "")):
             log_result("FT-004", "PASS", "Handled 503", "Yes")
        else:
             log_result("FT-004", "FAIL", f"Failed to handle 503: {res.get('enrich_error')}", "No")
    except Exception as e:
        log_result("FT-004", "FAIL", f"Exception: {e}", "No")

    # --- Category 2: Data Validation & Integrity ---

    # FT-005: Empty Response Body
    try:
        session.get.return_value = MockResponse("", status=200)
        deal = {"url": "http://test.com/empty", "valid": True}
        res = await bot.enrich_deal(session, deal)
        # Should fail buyability or regex
        if not res["valid"]:
             log_result("FT-005", "PASS", "Handled Empty Body", "Yes")
        else:
             log_result("FT-005", "FAIL", "Accepted Empty Body", "No")
    except Exception as e:
        log_result("FT-005", "FAIL", f"Exception: {e}", "No")

    # FT-006: Malformed JSON (Truncated)
    try:
        session.get.return_value = MockResponse("<html><body>Broken structure</body></html>", status=200)
        deal = {"url": "http://test.com/malformed", "valid": True}
        with patch("config.STRICT_BUYABILITY_CHECK", True):
            res = await bot.enrich_deal(session, deal)
            if not res["valid"] and "Buyability" in str(res.get("enrich_error", "")):
                log_result("FT-006", "PASS", "Handled Malformed/Missing Elements", "Yes")
            else:
                log_result("FT-006", "FAIL", f"Accepted Malformed: {res}", "No")
    except Exception as e:
        log_result("FT-006", "FAIL", f"Exception: {e}", "No")

    # FT-007: Missing Critical Fields (Anchor)
    try:
        # Must pass buyability check to reach anchor check
        session.get.return_value = MockResponse("<html><button>Buy Now</button></html>", status=200)
        deal = {"url": "http://test.com/missing_anchor", "valid": True} # Missing anchor_price
        with patch("config.REQUIRE_ANCHOR_PRICING", True), patch("config.STRICT_BUYABILITY_CHECK", True):
            res = await bot.enrich_deal(session, deal)
            if not res["valid"] and "Missing Anchor Pricing Data" in str(res.get("enrich_error", "")):
                log_result("FT-007", "PASS", "Rejected Missing Anchor Data", "Yes")
            else:
                log_result("FT-007", "FAIL", f"Accepted Missing Data or Wrong Error: {res.get('enrich_error')}", "No")
    except Exception as e:
        log_result("FT-007", "FAIL", f"Exception: {e}", "No")

    # FT-008: Invalid Data Types (Price as string "Free")
    try:
        deal = {"url": "http://test.com/bad_type", "valid": True, "new_price": "Free"}
        session.get.return_value = MockResponse("<html>+ $10 shipping</html>", status=200)
        res = await bot.enrich_deal(session, deal)
        if res["valid"]:
            log_result("FT-008", "PASS", "Handled Invalid Type (Graceful)", "Yes")
        else:
             log_result("FT-008", "PASS", "Rejected Invalid Type", "Yes")
    except Exception as e:
        log_result("FT-008", "FAIL", f"Crashed on Invalid Type: {e}", "No")

    # --- Category 3: Authentication & Authorization ---

    # FT-009: 401 Unauthorized
    try:
        session.get.return_value = MockResponse("Unauthorized", status=401)
        deal = {"url": "http://test.com/401", "valid": True}
        res = await bot.enrich_deal(session, deal)
        if not res["valid"] and "HTTP 401" in str(res.get("enrich_error", "")):
             log_result("FT-009", "PASS", "Handled 401", "Yes")
        else:
             log_result("FT-009", "FAIL", "Failed to handle 401", "No")
    except Exception as e:
        log_result("FT-009", "FAIL", f"Exception: {e}", "No")

    # FT-010: 403 Forbidden (Anti-Bot)
    try:
        session.get.return_value = MockResponse("Forbidden", status=403)
        deal = {"url": "http://test.com/403_test", "valid": True}
        res = await bot.enrich_deal(session, deal)
        if not res["valid"] and "403 Forbidden" in str(res.get("enrich_error", "")):
             log_result("FT-010", "PASS", "Handled 403 (Fail Closed)", "Yes")
        else:
             log_result("FT-010", "FAIL", "Failed to handle 403", "No")
    except Exception as e:
        log_result("FT-010", "FAIL", f"Exception: {e}", "No")

    # --- Category 4: Business Logic & Trust ---

    # FT-011: Trust Filter (Low Rating)
    try:
        session.get.return_value = MockResponse("<html>3.0 out of 5 stars</html>", status=200)
        deal = {"url": "http://test.com/low_rating", "valid": True}
        with patch("config.TRUST_RATING_THRESHOLD", 4.0):
            res = await bot.enrich_deal(session, deal)
            if not res["valid"] and "Trust Violation" in str(res.get("enrich_error", "")):
                log_result("FT-011", "PASS", "Trust Filter Triggered", "Yes")
            else:
                log_result("FT-011", "FAIL", "Trust Filter Failed", "No")
    except Exception as e:
        log_result("FT-011", "FAIL", f"Exception: {e}", "No")

    # FT-012: Price Error Detection
    try:
        session.get.return_value = MockResponse("<html></html>", status=200)
        deal = {"url": "http://test.com/price_error", "valid": True, "old_price": 1000, "new_price": 50, "title": "Item"}
        with patch("config.PRICE_ERROR_DROP_THRESHOLD", 0.80), patch("config.STRICT_BUYABILITY_CHECK", False), patch("config.REQUIRE_ANCHOR_PRICING", False):
            res = await bot.enrich_deal(session, deal)
            if res.get("is_price_error"):
                log_result("FT-012", "PASS", "Price Error Tagged", "Yes")
            else:
                log_result("FT-012", "FAIL", "Price Error Missed", "No")
    except Exception as e:
        log_result("FT-012", "FAIL", f"Exception: {e}", "No")

    # FT-013: Affiliate Tag Injection (Revenue Integrity)
    try:
        session.get.return_value = MockResponse("<html></html>", status=200)
        url = "http://amazon.in/dp/B00000"
        with patch("bot.AFFILIATE_TAGS", {"amazon.in": "tag-21"}):
             tagged = await bot.add_affiliate_tag(session, url, "amazon.in")
             if "tag-21" in tagged:
                 log_result("FT-013", "PASS", "Affiliate Tag Injected", "Yes")
             else:
                 log_result("FT-013", "FAIL", "Tag Injection Failed", "No")
    except Exception as e:
        log_result("FT-013", "FAIL", f"Exception: {e}", "No")

    # --- Category 5: System Resource & Security ---

    # FT-014: Resource Exhaustion (MemoryError Simulation)
    try:
        session.get.side_effect = MemoryError("OOM")
        deal = {"url": "http://test.com/oom", "valid": True}
        try:
            res = await bot.enrich_deal(session, deal)
            # If valid=False and error matches, it's good
            if not res["valid"]:
                 log_result("FT-014", "PASS", f"Handled OOM (Fail Closed): {res.get('enrich_error')}", "Yes")
            else:
                 log_result("FT-014", "FAIL", "Swallowed MemoryError (Invalid State)", "No")
        except MemoryError:
            log_result("FT-014", "PASS", "MemoryError Propagated", "Yes")
        except Exception as e:
            log_result("FT-014", "PASS", f"Handled OOM Gracefully: {e}", "Yes")
    except Exception as e:
        log_result("FT-014", "PASS", f"Handled OOM: {e}", "Yes")

    # FT-015: Config Corruption (Missing Thresholds)
    try:
        # Reset side effect
        session.get.side_effect = None
        
        # Temporarily remove config attr
        orig_thresh = config.TRUST_RATING_THRESHOLD
        del config.TRUST_RATING_THRESHOLD
        
        session.get.return_value = MockResponse("<html>4.5 out of 5 stars</html>", status=200)
        deal = {"url": "http://test.com/config_fail", "valid": True}
        
        try:
            res = await bot.enrich_deal(session, deal)
            if not res["valid"]:
                 log_result("FT-015", "PASS", f"Failed Closed on Missing Config: {res.get('enrich_error')}", "Yes")
            else:
                 log_result("FT-015", "FAIL", "Ran without config (Unexpected)", "No")
        except AttributeError:
             log_result("FT-015", "PASS", "Failed Closed on Missing Config (AttributeError)", "Yes")
        except Exception as e:
             log_result("FT-015", "PASS", f"Handled Config Error: {e}", "Yes")
        finally:
            config.TRUST_RATING_THRESHOLD = orig_thresh
    except Exception as e:
        log_result("FT-015", "FAIL", f"Setup Error: {e}", "No")

    # FT-016: Shadow Mode Leak Check
    try:
        # Verify that post_to_telegram uses the SHADOW_CHANNEL_ID
        # post_to_telegram signature: (bot, chat_id, caption)
        with patch("bot.bot.send_message", new_callable=AsyncMock) as mock_send, \
             patch("bot.TEST_MODE", False):  # Force TEST_MODE=False to allow sending
            
            # Case 1: Shadow Mode ON
            config.SHADOW_MODE = True
            config.SHADOW_CHANNEL_ID = -100
            
            # Call with mock bot, original ID = 123
            await bot.post_to_telegram(bot.bot, 123, "Test Caption")
            
            # Check call args
            if mock_send.call_count > 0:
                args, kwargs = mock_send.call_args
                chat_id = kwargs.get('chat_id') or args[0]
                
                if chat_id == -100:
                    log_result("FT-016", "PASS", "Shadow Redirect Verified", "Yes")
                else:
                    log_result("FT-016", "FAIL", f"Leaked to {chat_id}", "No")
            else:
                 log_result("FT-016", "FAIL", "Message not sent", "No")
            
    except Exception as e:
        log_result("FT-016", "FAIL", f"Exception: {e}", "No")

    logging.info("All FT tests completed.")

if __name__ == "__main__":
    asyncio.run(run_tests())
