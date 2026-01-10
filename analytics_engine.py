import pandas as pd
import os
from datetime import datetime, timedelta
import logging

# Config
CLICK_LOG_FILE = "click_logs.csv"
POST_LOG_FILE = "post_audit.log"
REJECTION_LOG_FILE = "rejection_audit.log"
SUMMARY_FILE = "daily_business_summary.csv"

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
    summary_row = {
        "date": today,
        "total_clicks": total_clicks,
        "unique_users": unique_users,
        "predicted_revenue": round(total_revenue, 2),
        "best_category": best_cat,
        "worst_category": worst_cat,
        "epc_per_category": str(epc_map),
        "deals_posted": total_posted,
        "deals_rejected": total_rejected
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
        run_scheduler()
    else:
        generate_daily_summary()
