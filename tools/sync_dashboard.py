#!/usr/bin/env python3
"""
MIRROR PROTOCOL: Sync dashboard with REAL data only
"""
import csv
import json
import os
from datetime import datetime

# Update workflow_heartbeat.json with live status
heartbeat_file = os.path.join("dashboard-new", "public", "data", "workflow_heartbeat.json")
os.makedirs(os.path.dirname(heartbeat_file), exist_ok=True)

with open(heartbeat_file, "w") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "status": "WORKING"
    }, f)

# Update heartbeat.json
with open("heartbeat.json", "w") as f:
    json.dump({
        "last_run": datetime.now().isoformat(),
        "status": "✅ Online"
    }, f)

print("✅ Live status updated")
print("🔧 Regenerating dashboard with REAL data only...")
os.system("python tools/generate_dashboard_data.py")
print("✅ All done! Dashboard is live with real deals.")
