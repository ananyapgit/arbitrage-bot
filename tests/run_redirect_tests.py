import asyncio
import logging
import os
import time
import csv
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import aiohttp
import sys
import os

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import system under test
import redirect_server
import analytics_engine

# Config
TEST_LOG_FILE = "test_click_logs.csv"
TEST_SUMMARY_FILE = "test_summary.csv"

# Redirect logs to test files
redirect_server.CLICK_LOG_FILE = TEST_LOG_FILE
analytics_engine.CLICK_LOG_FILE = TEST_LOG_FILE
analytics_engine.SUMMARY_FILE = TEST_SUMMARY_FILE

async def run_tests():
    # Force basicConfig to ensure output
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    print("DEBUG: Starting Tests...") # Direct print
    logging.info("Starting Failure Taxonomy Tests (FT-RI-01 to FT-RI-05)")

    app = redirect_server.create_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    try:
        # FT-RI-01: Click Logging Failure (Fail Closed)
        logging.info("--- FT-RI-01: Click Logging Failure ---")
        with patch("aiofiles.open", side_effect=IOError("Disk Write Failed")):
            resp = await client.get("/r?url=http://example.com&user_id=u1")
            # Should still redirect (302) or at least not 500. 
            # Note: TestClient follows redirects by default? No, usually returns 200 of target.
            # We check history or allow_redirects=False.
            resp = await client.get("/r?url=http://example.com&user_id=u1", allow_redirects=False)
            
            if resp.status == 302:
                logging.info("PASS: FT-RI-01 (Received 302 despite logging failure)")
            else:
                logging.error(f"FAIL: FT-RI-01 (Status {resp.status})")

        # FT-RI-02: Redirect Service Downtime (Logging Timeout)
        logging.info("--- FT-RI-02: Redirect Service Downtime (Logging Timeout) ---")
        
        async def slow_log(*args):
            await asyncio.sleep(1.0) # Sleep longer than timeout (0.2s)
        
        with patch("redirect_server.log_click", side_effect=slow_log):
            start = time.perf_counter()
            resp = await client.get("/r?url=http://example.com&user_id=u2", allow_redirects=False)
            duration = time.perf_counter() - start
            
            if resp.status == 302 and duration < 0.5:
                logging.info(f"PASS: FT-RI-02 (Received 302 in {duration:.3f}s despite slow log)")
            else:
                logging.error(f"FAIL: FT-RI-02 (Status {resp.status}, Duration {duration:.3f}s)")

        # FT-RI-03: EPC Misestimation (Analytics Accuracy)
        logging.info("--- FT-RI-03: EPC Misestimation ---")
        # Setup: Create dummy logs
        # 10 Electronics (EPC 5.0) -> 50.0
        # 4 Fashion (EPC 2.5) -> 10.0
        # Total = 60.0
        
        if os.path.exists(TEST_LOG_FILE): os.remove(TEST_LOG_FILE)
        
        # Write logs manually
        with open(TEST_LOG_FILE, "w") as f:
            f.write("timestamp,user_id,category,platform,target_url\n")
            for _ in range(10):
                f.write(f"{datetime.now().isoformat()},uX,electronics,web,http://ex.com\n")
            for _ in range(4):
                f.write(f"{datetime.now().isoformat()},uY,fashion,web,http://ex.com\n")
        
        # Run Analytics
        analytics_engine.generate_daily_summary()
        
        # Verify
        if os.path.exists(TEST_SUMMARY_FILE):
            df = pd.read_csv(TEST_SUMMARY_FILE)
            rev = df.iloc[0]['predicted_revenue']
            clicks = df.iloc[0]['total_clicks']
            
            if abs(rev - 60.0) < 0.1 and clicks == 14:
                logging.info(f"PASS: FT-RI-03 (Revenue {rev}, Clicks {clicks})")
            else:
                logging.error(f"FAIL: FT-RI-03 (Revenue {rev} != 60.0)")
        else:
            logging.error("FAIL: FT-RI-03 (Summary file not created)")

        # FT-RI-04: Category Throttling (Load Test)
        logging.info("--- FT-RI-04: Category Throttling (Load Resilience) ---")
        # Send 50 concurrent requests
        # We expect all to pass (Fail Closed = Don't drop traffic)
        
        # We need to un-patch any previous mocks, which `with` blocks handle.
        # But we also need real logging to work or at least mocked logging that works fast.
        # Let's mock log_click to be fast no-op
        
        async def fast_log(*args):
            pass
            
        with patch("redirect_server.log_click", side_effect=fast_log):
            tasks = []
            for i in range(50):
                tasks.append(client.get(f"/r?url=http://example.com&category=test&user_id={i}", allow_redirects=False))
            
            start = time.perf_counter()
            responses = await asyncio.gather(*tasks)
            duration = time.perf_counter() - start
            
            failures = [r.status for r in responses if r.status != 302]
            
            if not failures:
                logging.info(f"PASS: FT-RI-04 (50 reqs in {duration:.3f}s, 0 failures)")
            else:
                logging.error(f"FAIL: FT-RI-04 ({len(failures)} failures)")

        # FT-RI-05: Latency Check
        logging.info("--- FT-RI-05: Latency Check ---")
        # Measure single request latency
        with patch("redirect_server.log_click", side_effect=fast_log):
            start = time.perf_counter()
            resp = await client.get("/r?url=http://example.com", allow_redirects=False)
            duration = (time.perf_counter() - start) * 1000 # ms
            
            if duration < 200: # Requirement: Fail closed without user-facing latency
                 logging.info(f"PASS: FT-RI-05 (Latency {duration:.2f}ms)")
            else:
                 logging.warning(f"WARN: FT-RI-05 (Latency {duration:.2f}ms > 200ms)")

    finally:
        await client.close()
        # Clean up
        if os.path.exists(TEST_LOG_FILE): os.remove(TEST_LOG_FILE)
        if os.path.exists(TEST_SUMMARY_FILE): os.remove(TEST_SUMMARY_FILE)

from datetime import datetime

if __name__ == "__main__":
    asyncio.run(run_tests())
