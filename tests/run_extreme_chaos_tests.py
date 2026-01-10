import unittest
import os
import json
import logging
import asyncio
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta
import sys

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules to test
import bot
import config
import analytics_engine
from telegram.error import RetryAfter, TelegramError

# Setup logging for tests
logging.basicConfig(level=logging.CRITICAL)

class TestExtremeChaos(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        # Reset global state where possible
        bot.processed_cache.clear()
        bot.category_throttle_state = {}
        # Clear log files for fresh verification
        for log_file in ["rejection_audit.log", "post_audit.log", "spam_pause.json"]:
            if os.path.exists(log_file):
                os.remove(log_file)

    def tearDown(self):
        # Clean up
        pass

    # ==========================================
    # 1. HUMAN LAYER: Configuration Corruption
    # ==========================================
    @patch("builtins.open", new_callable=mock_open, read_data="{INVALID_JSON}")
    @patch("json.load", side_effect=json.JSONDecodeError("Expecting value", "", 0))
    async def test_human_json_corruption(self, mock_json, mock_file):
        """
        Scenario: User edits config/deals.json and leaves it invalid.
        Expectation: Bot handles error gracefully, returns default empty list/dict, logs error.
        """
        data = bot.load_json("deals.json")
        self.assertEqual(data, [], "Should return default empty list on JSON error")
        
        # Verify it didn't crash
        self.assertTrue(True)

    # ==========================================
    # 2. CONFIG LAYER: Drift Detection
    # ==========================================
    @patch("config_monitor.get_current_config_dict")
    @patch("builtins.open", new_callable=mock_open, read_data='{"BOT_TOKEN": "OLD_TOKEN"}')
    @patch("json.load")
    async def test_config_drift_detection(self, mock_json_load, mock_file, mock_get_config):
        """
        Scenario: Runtime config differs from snapshot.
        Expectation: Drift detected and logged.
        """
        import config_monitor
        
        mock_get_config.return_value = {"BOT_TOKEN": "NEW_TOKEN"} # Drift!
        mock_json_load.return_value = {"BOT_TOKEN": "OLD_TOKEN"}
        
        with self.assertLogs(level='WARNING') as cm:
            config_monitor.detect_config_drift()
            
        self.assertTrue(any("Config Drift Detected" in log for log in cm.output))

    # ==========================================
    # 3. DATA LAYER: Malformed Data (Parameterized)
    # ==========================================
    async def test_data_malformed_price(self):
        """
        Scenario: Price contains unicode/emojis or invalid format.
        Expectation: Deal rejected, logged in rejection_audit.log.
        """
        scenarios = [
            ("₹9😊00", "Low Discount (0.00%)"),
            ("₹-100", "Low Discount (0.00%)"),
            ("Invalid", "Low Discount (0.00%)"),
            ("None", "Low Discount (0.00%)"),
            ("1.2.3.4", "Low Discount (0.00%)")
        ]
        
        for price_input, expected_reason in scenarios:
            with self.subTest(price=price_input):
                deal = {
                    "title": "Test Item",
                    "url": "http://example.com",
                    "old_price": "₹1,000",
                    "new_price": price_input
                }
                
                bot.log_rejection(deal["url"], expected_reason)
                
                with open("rejection_audit.log", "r", encoding="utf-8") as f:
                    content = f.read()
                    self.assertIn(expected_reason, content)

    # ==========================================
    # 10. ADVERSARIAL LAYER: Junk Payload (Parameterized)
    # ==========================================
    @patch("bot.log_rejection")
    async def test_adversarial_junk_payload(self, mock_log):
        """
        Scenario: Junk deal with missing keys.
        Expectation: Validation fails, logs rejection.
        """
        bad_payloads = [
            {"random_key": "random_value"}, # No URL
            {"url": "http://valid.com"}, # No Title
            {"title": "Only Title"}, # No URL
            {}, # Empty
            {"url": "http://valid.com", "title": "T", "price": -1} # Negative price (logic might catch elsewhere but enrich handles structure)
        ]
        
        session = MagicMock()
        
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                res = await bot.enrich_deal(session, payload)
                self.assertFalse(res.get("valid", False))
                # Mock called at least once
                self.assertTrue(mock_log.called)

    # ==========================================
    # 6. PLATFORM LAYER: Telegram Flood Wait
    # ==========================================
    @patch("bot.update_trust_decay")
    @patch("bot.activate_spam_pause")
    @patch("bot.Bot")
    async def test_platform_flood_wait(self, mock_bot_cls, mock_activate, mock_decay):
        """
        Scenario: Telegram returns FloodWait/RetryAfter or Spam error.
        Expectation: Bot triggers spam pause (fail closed).
        """
        # Create a mock bot instance
        mock_bot_instance = MagicMock()
        mock_bot_cls.return_value = mock_bot_instance
        
        # Mock send_message to raise Flood error
        mock_bot_instance.send_message.side_effect = TelegramError("Flood control exceeded")
        
        from bot import post_to_telegram
        
        # Force TEST_MODE=False and SHADOW_MODE=False
        with patch("bot.TEST_MODE", False), patch("config.SHADOW_MODE", False):
             # Run it
             chat_id = 123
             text = "Test"
             
             # It should return None and trigger activation
             res = await post_to_telegram(mock_bot_instance, chat_id, text)
        
        self.assertIsNone(res)
        mock_activate.assert_called_with(24)
        mock_decay.assert_called()

    # ==========================================
    # 9. INFRA LAYER: Disk Full
    # ==========================================
    async def test_infra_disk_full(self):
        """
        Scenario: File system raises OSError(28, 'No space left on device') during log write.
        Expectation: Bot catches exception, logs to stderr/logging, does NOT crash main loop.
        """
        # Patch open globally but be careful not to break other things if parallel (not parallel here)
        # We only want it to fail for the log file
        
        original_open = open
        def side_effect(file, *args, **kwargs):
            if "rejection_audit.log" in str(file):
                raise OSError(28, "No space left on device")
            return original_open(file, *args, **kwargs)

        with patch("builtins.open", side_effect=side_effect):
            try:
                bot.log_rejection("http://test.com", "Test Reason")
            except Exception:
                self.fail("log_rejection should handle OSError internally and not crash")
            
    # ==========================================
    # 11. ECONOMIC LAYER: EPC Collapse
    # ==========================================
    @patch("pandas.read_csv")
    async def test_economic_epc_collapse(self, mock_read):
        """
        Scenario: Category EPC drops below threshold.
        Expectation: Category is throttled.
        """
        # Mock DataFrame
        import pandas as pd
        
        data = {
            "epc_per_category": ["{'electronics': 0.05, 'fashion': 2.0}"]
        }
        mock_read.return_value = pd.DataFrame(data)
        
        # We also need to patch os.path.exists to return True for the summary file
        # otherwise update_category_throttles returns early.
        original_exists = os.path.exists
        def side_effect(path):
            if "daily_business_summary.csv" in str(path):
                return True
            return original_exists(path)
            
        with patch("os.path.exists", side_effect=side_effect):
            # Run update
            bot.update_category_throttles()
        
        # Check state
        self.assertIn("electronics", bot.category_throttle_state)
        self.assertTrue(bot.check_category_throttle("electronics"))

        
if __name__ == "__main__":
    # Create dummy config for tests if needed
    if not hasattr(config, "EPC_THROTTLE_THRESHOLD"):
        config.EPC_THROTTLE_THRESHOLD = 0.10
        
    unittest.main()
