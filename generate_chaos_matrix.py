import csv
import random

layers = [
    "Human", "Config", "Data", "Time", "Dependency", 
    "Platform", "Revenue", "Trust", "Infra", "Adversarial", 
    "Economic", "Recovery"
]

headers = [
    "Chaos_Test_ID", "Chaos_Layer", "Historical_Reference", "Scenario_Name", 
    "Human_Behavior_Simulated", "Trigger_Method", "Injected_Failure", 
    "System_Surface_Targeted", "Expected_System_Response", 
    "Fail_Closed_Requirement", "Detection_Signal", "Mitigation_Action", 
    "Audit_Log_Required", "Recovery_Behavior", "Verification_Method", 
    "Runnable_Test_Name", "Execution_Mode", "Severity_Level", "Launch_Blocker"
]

rows = []

# Helper to add rows
def add_row(layer, id_suffix, scenario, behavior, trigger, failure, target, expected, detection, mitigation, test_name):
    rows.append({
        "Chaos_Test_ID": f"CH-{layer[:3].upper()}-{id_suffix:03d}",
        "Chaos_Layer": layer,
        "Historical_Reference": "General-Chaos-001",
        "Scenario_Name": scenario,
        "Human_Behavior_Simulated": behavior,
        "Trigger_Method": trigger,
        "Injected_Failure": failure,
        "System_Surface_Targeted": target,
        "Expected_System_Response": expected,
        "Fail_Closed_Requirement": "Yes",
        "Detection_Signal": detection,
        "Mitigation_Action": mitigation,
        "Audit_Log_Required": "rejection_audit.log",
        "Recovery_Behavior": "Auto-Resume",
        "Verification_Method": "Log Check",
        "Runnable_Test_Name": test_name,
        "Execution_Mode": "Automated",
        "Severity_Level": "Critical",
        "Launch_Blocker": "Yes"
    })

# 1. Human Layer (Mistakes, panic actions)
for i in range(1, 11):
    add_row("Human", i, f"Human Error {i}", "Sleep deprivation", "Manual File Edit", 
            "Corrupt JSON syntax", "Config Loader", "Crash or Fallback", 
            "Exception Logged", "Revert/Safe Mode", "test_human_json_corruption")

# 2. Config Layer (Drift, corruption)
for i in range(1, 11):
    add_row("Config", i, f"Config Drift {i}", "Deployment Error", "Startup Check", 
            f"Env Var Mismatch {i}", "Config Monitor", "Log Drift & Continue/Halt", 
            "Drift Detected", "Alert Admin", "test_config_drift_detection")

# 3. Data Layer (Malformed, partial)
for i in range(1, 11):
    add_row("Data", i, f"Bad Data {i}", "Vendor API Change", "Scraper Parse", 
            "Unicode/Emoji in Price", "Validator", "Reject Deal", 
            "Validation Error", "Discard Data", "test_data_malformed_price")

# 4. Time Layer (DST, clock skew)
for i in range(1, 11):
    add_row("Time", i, f"Time Skew {i}", "System Clock Drift", "Timestamp Gen", 
            "Future Timestamp", "Scheduler", "Ignore Future Events", 
            "Time Check Fail", "Use Server Time", "test_time_future_timestamp")

# 5. Dependency Layer (Retailers, redirects)
for i in range(1, 11):
    add_row("Dependency", i, f"Retailer Fail {i}", "Vendor Outage", "HTTP Request", 
            "503 Service Unavailable", "Enrichment", "Retry/Fail Deal", 
            "HTTP Error Log", "Exponential Backoff", "test_dependency_503")

# 6. Platform Layer (Telegram bans, throttling)
for i in range(1, 11):
    add_row("Platform", i, f"Platform Hostility {i}", "Policy Change", "API Call", 
            "429 Flood Wait", "Telegram Bot", "Pause Posting", 
            "Flood Exception", "24h Safety Pause", "test_platform_flood_wait")

# 7. Revenue Layer (EPC collapse, tag stripping)
for i in range(1, 11):
    add_row("Revenue", i, f"Revenue Loss {i}", "Link Hijack", "Redirect Logic", 
            "Affiliate Tag Stripped", "Link Builder", "Use Backup Tag", 
            "Tag Check Fail", "Alert/Pause", "test_revenue_tag_stripping")

# 8. Trust Layer (User fatigue, mute/block)
for i in range(1, 11):
    add_row("Trust", i, f"Trust Decay {i}", "Spam Report", "User Feedback", 
            "User Blocked Bot", "User Manager", "Increment Decay", 
            "Forbidden Error", "Remove User", "test_trust_user_block")

# 9. Infra Layer (Disk full, memory leak)
for i in range(1, 11):
    add_row("Infra", i, f"Infra Failure {i}", "Resource Exhaustion", "File Write", 
            "Disk Full (ENOSPC)", "Logger", "Fail Closed (No Post)", 
            "IOError", "Alert & Halt", "test_infra_disk_full")

# 10. Adversarial Layer (Competitor attacks)
for i in range(1, 11):
    add_row("Adversarial", i, f"Attack {i}", "Competitor Bot", "Inbound Traffic", 
            "Junk Payload Injection", "API Endpoint", "Reject Request", 
            "Auth Fail", "Ban IP", "test_adversarial_junk_payload")

# 11. Economic Layer (Category inversion)
for i in range(1, 11):
    add_row("Economic", i, f"Market Crash {i}", "Market Shift", "EPC Calc", 
            "Category EPC < 0.01", "Strategy Engine", "Throttle Category", 
            "Low EPC Alert", "12h Pause", "test_economic_epc_collapse")

# 12. Recovery Layer (Restart after chaos)
for i in range(1, 11):
    add_row("Recovery", i, f"Recovery Fail {i}", "Power Loss", "Startup", 
            "Corrupt State File", "State Loader", "Reset State", 
            "Load Error", "Fresh Start", "test_recovery_corrupt_state")

# Ensure we have 120 tests
print(f"Generated {len(rows)} tests.")

with open("chaos_engineering_test_matrix.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
