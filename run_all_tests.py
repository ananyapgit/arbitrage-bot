import subprocess
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TEST_SUITES = [
    "tests/run_failure_taxonomy_tests.py",
    "tests/run_redirect_tests.py",
    "tests/run_shadow_chaos_tests.py",
    # "tests/run_phase6_validation.py" # Optional, might be redundant or long-running
]

def run_test_suite(script_path):
    """Runs a python test script and returns True if passed."""
    logging.info(f"🧪 Running Test Suite: {script_path} ...")
    try:
        # Use the same python interpreter
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info(f"✅ PASS: {script_path}")
            return True
        else:
            logging.error(f"❌ FAIL: {script_path}")
            logging.error(f"Output:\n{result.stdout}\n{result.stderr}")
            return False
    except Exception as e:
        logging.error(f"❌ ERROR: Could not run {script_path}: {e}")
        return False

def main():
    logging.info("🚀 STARTING FINAL SYSTEM AUDIT & TEST RUNNER")
    
    passed_count = 0
    total_count = len(TEST_SUITES)
    
    for suite in TEST_SUITES:
        if run_test_suite(suite):
            passed_count += 1
            
    logging.info("="*40)
    logging.info(f"SUMMARY: {passed_count}/{total_count} Suites Passed")
    logging.info("="*40)
    
    if passed_count == total_count:
        logging.info("✅ ALL SYSTEMS GO. READY FOR PRODUCTION.")
        sys.exit(0)
    else:
        logging.error("⛔ SYSTEM FAILURE. DO NOT DEPLOY.")
        sys.exit(1)

if __name__ == "__main__":
    main()
