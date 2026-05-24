#!/usr/bin/env python3
"""
Set bot status for dashboard with configurable status values.
Usage: python tools/set_bot_status.py [status]
Status options: SCRAPING, RUNNING, BROADCASTING, IDLE, SLEEPING
"""
import json
import os
import sys
from datetime import datetime

def main():
    # Determine status from command line, default to SCRAPING
    status = "SCRAPING"
    if len(sys.argv) > 1:
        status = sys.argv[1].upper()
    
    # Map statuses to dashboard-readable values
    status_map = {
        "SCRAPING": "Scraping",
        "RUNNING": "Working",
        "BROADCASTING": "Broadcasting",
        "IDLE": "Sleeping",
        "SLEEPING": "Sleeping",
        "FINISHED": "Sleeping"
    }
    display_status = status_map.get(status, "Sleeping")
    
    # Update workflow_heartbeat.json
    heartbeat_file = os.path.join("dashboard-new", "public", "data", "workflow_heartbeat.json")
    os.makedirs(os.path.dirname(heartbeat_file), exist_ok=True)
    
    with open(heartbeat_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "status": status
        }, f)
    
    # Also update heartbeat.json
    with open("heartbeat.json", "w") as f:
        json.dump({
            "last_run": datetime.now().isoformat(),
            "status": f"✅ {display_status}" if display_status != "Sleeping" else "⏸️ Sleeping"
        }, f)
    
    # Also update stats.json with current status
    stats_file = os.path.join("dashboard-new", "public", "data", "stats.json")
    try:
        if os.path.exists(stats_file):
            with open(stats_file, "r") as f:
                stats = json.load(f)
            stats["workflowStatus"] = display_status
            with open(stats_file, "w") as f:
                json.dump(stats, f)
    except Exception as e:
        pass
    
    print(f"✅ Bot status updated to: {display_status}")

if __name__ == "__main__":
    main()
