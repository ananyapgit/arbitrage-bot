import pandas as pd
import os
from datetime import datetime, timedelta
import logging
import json
from telegram import Bot
import config

# Config
CLICK_LOG_FILE = "click_logs.csv"
POST_LOG_FILE = "post_audit.log"
REJECTION_LOG_FILE = "rejection_audit.log"
SUMMARY_FILE = "daily_business_summary.csv"
SOCIAL_PROOF_STATE_FILE = "social_proof_state.json"

# Category Priors (Expected EPC - Earnings Per Click)
CATEGORY_PRIORS = {
    "electronics": 5.0,
    "fashion": 2.5,
    "home": 3.0,
    "general": 1.0
}

def generate_daily_summary():
    """
    Parses click logs, post logs, and rejection logs to generate a daily summary.
    """
    today = datetime.now().date()
    
    # --- 1. CLICK METRICS ---
    total_clicks = 0
    unique_users = 0
    total_revenue = 0
    best_cat = "N/A"
    worst_cat = "N/A"
    epc_map = {}
    
    if os.path.exists(CLICK_LOG_FILE):
        try:
            df = pd.read_csv(CLICK_LOG_FILE)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            # df = df[df['timestamp'].dt.date == today] # In prod, filter by date
            
            if not df.empty:
                summary = df.groupby('category').agg(
                    total_clicks=('timestamp', 'count'),
                    unique_users=('user_id', 'nunique')
                ).reset_index()
                
                summary['predicted_revenue'] = summary.apply(
                    lambda row: row['total_clicks'] * CATEGORY_PRIORS.get(row['category'], 1.0), axis=1
                )
                
                total_clicks = summary['total_clicks'].sum()
                unique_users = df['user_id'].nunique()
                total_revenue = summary['predicted_revenue'].sum()
                
                if not summary.empty:
                    best_cat = summary.loc[summary['predicted_revenue'].idxmax()]['category']
                    worst_cat = summary.loc[summary['predicted_revenue'].idxmin()]['category']
                    
                # Calculate EPC per category
                for _, row in summary.iterrows():
                    epc = row['predicted_revenue'] / row['total_clicks'] if row['total_clicks'] > 0 else 0
                    epc_map[row['category']] = round(epc, 2)
                    
        except Exception as e:
            logging.error(f"Error processing click logs: {e}")

    # --- 2. POST vs REJECTION METRICS ---
    total_posted = 0
    total_rejected = 0
    
    if os.path.exists(POST_LOG_FILE):
        try:
            pdf = pd.read_csv(POST_LOG_FILE)
            # Filter by date if needed
            total_posted = len(pdf)
        except Exception as e:
            logging.error(f"Error processing post logs: {e}")
            
    if os.path.exists(REJECTION_LOG_FILE):
        try:
            rdf = pd.read_csv(REJECTION_LOG_FILE)
            # Filter by date if needed
            total_rejected = len(rdf)
        except Exception as e:
            logging.error(f"Error processing rejection logs: {e}")

    # --- 3. WRITE SUMMARY ---
    # Behavioral counters
    personalized_dms = 0
    urgency_count = 0
    social_escalations = 0
    price_error_alerts = 0
    try:
        # Personalized DMs from waitlist
        if os.path.exists(config.WAITLIST_DB_FILE):
            wdata = load_json(config.WAITLIST_DB_FILE, default=[])
            personalized_dms = sum(1 for e in wdata if e.get("alerted"))
        # Urgency count from followup cache titles
        if os.path.exists(config.SALE_FOLLOWUP_CACHE_FILE):
            fdata = load_json(config.SALE_FOLLOWUP_CACHE_FILE, default={})
            urgency_count = sum(1 for _, v in fdata.items() if isinstance(v, dict) and "[🔥 LOW STOCK" in str(v.get("title", "")))
        # Social proof escalations from state
        if os.path.exists(SOCIAL_PROOF_STATE_FILE):
            sdata = load_json(SOCIAL_PROOF_STATE_FILE, default={})
            social_escalations = len(sdata.keys())
        # Price error alerts from rejection audit
        if os.path.exists(REJECTION_LOG_FILE):
            try:
                rdf = pd.read_csv(REJECTION_LOG_FILE)
                price_error_alerts = int((rdf['reason'].astype(str).str.contains("price_out_of_bounds")).sum())
            except Exception:
                pass
    except Exception as e:
        logging.error(f"Behavioral counters aggregation failed: {e}")

    summary_row = {
        "date": today,
        "total_clicks": total_clicks,
        "unique_users": unique_users,
        "predicted_revenue": round(total_revenue, 2),
        "best_category": best_cat,
        "worst_category": worst_cat,
        "epc_per_category": str(epc_map),
        "deals_posted": total_posted,
        "deals_rejected": total_rejected,
        "Personalized_DMs_Sent": personalized_dms,
        "Price_Error_Alerts_Triggered": price_error_alerts,
        "Urgency_Triggered_Count": urgency_count,
        "Social_Proof_Escalations": social_escalations
    }
    
    try:
        file_exists = os.path.isfile(SUMMARY_FILE)
        summary_df = pd.DataFrame([summary_row])
        
        mode = 'a' if file_exists else 'w'
        header = not file_exists
        
        summary_df.to_csv(SUMMARY_FILE, mode=mode, header=header, index=False)
        logging.info(f"Generated daily summary for {today}")
    except Exception as e:
        logging.error(f"Failed to write summary: {e}")

import time
import asyncio
from datetime import datetime, timedelta

def load_json(path, default=None):
    if default is None: default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save {path}: {e}")

async def social_proof_loop():
    """
    Monitors click logs and escalates social proof by editing Telegram messages
    when clicks > MIN_CLICKS_FOR_SOCIAL_PROOF within the last 30 minutes.
    Prevents repeated edits for the same URL threshold.
    """
    logging.info("Social Proof Loop Started")
    bot = Bot(token=config.BOT_TOKEN)
    state = load_json(SOCIAL_PROOF_STATE_FILE, default={})
    while True:
        try:
            if not os.path.exists(CLICK_LOG_FILE) or not os.path.exists(config.SALE_FOLLOWUP_CACHE_FILE):
                await asyncio.sleep(60)
                continue
            df = pd.read_csv(CLICK_LOG_FILE)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            window_start = datetime.now() - timedelta(minutes=30)
            recent = df[df['timestamp'] >= window_start]
            if recent.empty:
                await asyncio.sleep(60)
                continue
            counts = recent.groupby('target_url').size().reset_index(name='count')
            followup = load_json(config.SALE_FOLLOWUP_CACHE_FILE, default={})
            for _, row in counts.iterrows():
                url = row['target_url']
                cnt = int(row['count'])
                if cnt >= config.MIN_CLICKS_FOR_SOCIAL_PROOF:
                    applied = state.get(url, 0)
                    # Only escalate once per threshold
                    if applied >= cnt:
                        continue
                    info = followup.get(url)
                    if info and "message_id" in info and "chat_id" in info:
                        try:
                            msg_id = info["message_id"]
                            chat_id = info["chat_id"]
                            text = f"🔥 {cnt} people are looking at this right now!"
                            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text)
                            state[url] = cnt
                            save_json(SOCIAL_PROOF_STATE_FILE, state)
                            logging.info(f"Escalated social proof for {url} to {cnt} clicks")
                        except Exception as e:
                            logging.warning(f"Social proof edit failed for {url}: {e}")
            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Social proof loop error: {e}")
            await asyncio.sleep(60)

def run_scheduler():
    """
    Runs the generator loop, executing daily summary at midnight.
    """
    logging.info("Analytics Scheduler Started")
    while True:
        now = datetime.now()
        # Calculate time until next midnight
        tomorrow = now.date() + timedelta(days=1)
        midnight = datetime.combine(tomorrow, datetime.min.time())
        seconds_until_midnight = (midnight - now).total_seconds()
        
        logging.info(f"Sleeping for {seconds_until_midnight:.2f} seconds until midnight...")
        time.sleep(seconds_until_midnight + 1) # +1 to ensure we are in the next day
        
        generate_daily_summary()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Check if we want to run once or schedule
    import sys
    if "--daemon" in sys.argv:
        # Run both scheduler and social proof loop
        loop = asyncio.get_event_loop()
        loop.create_task(social_proof_loop())
        try:
            run_scheduler()
        except KeyboardInterrupt:
            pass
    else:
        generate_daily_summary()
