import os
import json
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)

def utc_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def file_size(path):
    try:
        return os.path.getsize(path)
    except Exception:
        return 0

def update_last_auto_update_line(doc_path, ts):
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith("Last Auto-Update:"):
            lines[i] = f"Last Auto-Update: {ts}"
            replaced = True
            break
    if not replaced:
        lines.append("")
        lines.append(f"Last Auto-Update: {ts}")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def append_failure_taxonomy_summary(doc_path, summary_lines):
    try:
        with open(doc_path, "a", encoding="utf-8") as f:
            f.write("\n")
            for line in summary_lines:
                f.write(line + "\n")
    except Exception:
        pass

def main():
    ts = utc_iso()
    rej_log = os.path.join(PROJECT_ROOT, "rejection_audit.log")
    exec_log = os.path.join(PROJECT_ROOT, "failure_test_execution_log.csv")
    report_json = os.path.join(PROJECT_ROOT, "launch_validation_report.json")
    cfg_log = os.path.join(PROJECT_ROOT, "config_change_log.csv")

    report = read_json(report_json, default={})
    total = int(report.get("total_tests", 0))
    passed = int(report.get("passed", 0))
    failed = int(report.get("failed", 0))
    blockers = report.get("blockers", []) or []
    blocker_count = len(blockers)

    docs = [
        os.path.join(PROJECT_ROOT, "docs", "failure_taxonomy.md"),
        os.path.join(PROJECT_ROOT, "docs", "logging_contract.md"),
        os.path.join(PROJECT_ROOT, "ARCHITECTURE.md"),
    ]
    for doc in docs:
        update_last_auto_update_line(doc, ts)

    ft_summary = []
    ft_summary.append(f"Auto-Update Summary: {ts}")
    ft_summary.append(f"- Tests: {passed} passed / {failed} failed / {total} total")
    ft_summary.append(f"- Blockers: {blocker_count}")
    ft_summary.append(f"- Artifacts: rejection_audit.log={file_size(rej_log)}B, failure_test_execution_log.csv={file_size(exec_log)}B, launch_validation_report.json={file_size(report_json)}B")
    if os.path.exists(cfg_log):
        ft_summary.append(f"- Config Change Log: {file_size(cfg_log)}B")
    append_failure_taxonomy_summary(os.path.join(PROJECT_ROOT, "docs", "failure_taxonomy.md"), ft_summary)

if __name__ == "__main__":
    main()

