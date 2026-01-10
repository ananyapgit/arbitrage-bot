import os
import json
import logging
import datetime
import inspect
import hashlib
import config

CONFIG_CHANGE_LOG = "config_change_log.csv"
CONFIG_SNAPSHOT_FILE = "config_snapshot.json"

def get_git_commit_hash():
    """Retrieves the current git commit hash."""
    try:
        # In a real environment, we might use subprocess to call git
        # For this environment, we might not have git installed or initialized
        # We'll simulate or try to read .git/HEAD
        if os.path.exists(".git/HEAD"):
            with open(".git/HEAD", "r") as f:
                ref = f.read().strip()
                if ref.startswith("ref:"):
                    ref_path = ".git/" + ref.split(" ")[1]
                    if os.path.exists(ref_path):
                        with open(ref_path, "r") as f2:
                            return f2.read().strip()
        return "unknown_commit"
    except Exception as e:
        logging.warning(f"Could not get git hash: {e}")
        return "unknown_commit"

def get_current_config_dict():
    """Extracts all uppercase variables from config module."""
    config_dict = {}
    for name, value in inspect.getmembers(config):
        if name.isupper():
            # Serialize non-serializable objects if necessary
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                config_dict[name] = value
            else:
                config_dict[name] = str(value)
    return config_dict

def log_change(key, old_val, new_val, commit_hash):
    """Logs a single config change to CSV."""
    timestamp = datetime.datetime.now().isoformat()
    change_source = "manual/deploy" # inferred
    restart_required = "yes" # Most config changes require restart
    
    log_entry = f"{timestamp},{key},{old_val},{new_val},{change_source},{commit_hash},{restart_required}\n"
    
    file_exists = os.path.exists(CONFIG_CHANGE_LOG)
    
    try:
        with open(CONFIG_CHANGE_LOG, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("timestamp,config_key,old_value,new_value,change_source,git_commit_hash,restart_required\n")
            f.write(log_entry)
    except IOError as e:
        logging.error(f"Failed to write to config log: {e}")

def detect_config_drift():
    """
    Compares current config against the last snapshot.
    Logs differences and updates the snapshot.
    """
    logging.info("🛡️ Running Configuration Drift Detection...")
    
    current_config = get_current_config_dict()
    commit_hash = get_git_commit_hash()
    
    # Load snapshot
    last_config = {}
    if os.path.exists(CONFIG_SNAPSHOT_FILE):
        try:
            with open(CONFIG_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                last_config = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config snapshot: {e}")
    
    drift_detected = False
    
    # Check for changes
    all_keys = set(current_config.keys()) | set(last_config.keys())
    
    for key in all_keys:
        old_val = last_config.get(key, "N/A")
        new_val = current_config.get(key, "N/A")
        
        # Simple equality check
        if old_val != new_val:
            logging.warning(f"🚨 Config Drift Detected: {key} changed from {old_val} to {new_val}")
            log_change(key, old_val, new_val, commit_hash)
            drift_detected = True
            
    # Update snapshot
    if drift_detected or not os.path.exists(CONFIG_SNAPSHOT_FILE):
        try:
            with open(CONFIG_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=4)
            logging.info("✅ Config snapshot updated.")
        except Exception as e:
            logging.error(f"Failed to update config snapshot: {e}")
            
    if not drift_detected:
        logging.info("✅ No configuration drift detected.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detect_config_drift()
