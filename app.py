import streamlit as st
import pandas as pd
import datetime
import os
import csv
import asyncio
import aiofiles
from urllib.parse import urlparse, parse_qs

# ================== CONFIGURATION ==================
CLICK_LOG_FILE = "click_logs.csv"
DAILY_BUSINESS_SUMMARY = "daily_business_summary.csv"
# Securely load secrets
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin")  # Fallback only for local testing if not set
SCRAPER_STATUS_FILE = "scraper_status.json" # Hypothetical status file

# ================== REDIRECT BRIDGE ==================
def redirect_bridge():
    # Streamlit's query params
    query_params = st.query_params
    target_url = query_params.get("url", None)
    
    if target_url:
        # 1. Capture Metadata
        user_id = query_params.get("user_id", "anonymous")
        category = query_params.get("category", "general")
        platform = query_params.get("platform", "web")
        timestamp = datetime.datetime.now().isoformat()
        
        # 2. Log Click (Synchronous for Streamlit simple execution flow, or could be async if needed)
        # Using standard file append for simplicity in Streamlit's linear execution model
        log_entry = [timestamp, user_id, category, platform, target_url]
        
        file_exists = os.path.isfile(CLICK_LOG_FILE)
        try:
            with open(CLICK_LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["timestamp", "user_id", "category", "platform", "target_url"])
                writer.writerow(log_entry)
        except Exception as e:
            print(f"Logging failed: {e}")
        
        # 3. Redirect
        # Meta-refresh is reliable for Streamlit apps
        redirect_html = f"""
            <meta http-equiv="refresh" content="0; url={final_url}">
            <script>window.location.href = "{final_url}";</script>
            <p>Redirecting to <a href="{final_url}">{final_url}</a>...</p>
        """
        st.markdown(redirect_html, unsafe_allow_html=True)
        st.stop() # Stop further execution
    else:
        # If no URL provided, show the dashboard login (default to dashboard if accessed directly)
        return

# ================== ADMIN DASHBOARD ==================
def admin_dashboard():
    st.title("Admin Dashboard 🚀")
    
    password = st.text_input("Enter Admin Password", type="password")
    
    if password == ADMIN_PASSWORD:
        st.success("Access Granted")
        
        # 1. Live Scraper Status
        st.subheader("Live Scraper Status")
        # In a real scenario, this might check a heartbeat file updated by the scraper
        # For now, we'll check if the main.py process is running or check a timestamp file
        try:
            if os.path.exists("heartbeat.timestamp"):
                with open("heartbeat.timestamp", "r") as f:
                    last_heartbeat = f.read().strip()
                st.metric("Last Heartbeat", last_heartbeat)
            else:
                st.warning("No heartbeat detected.")
        except Exception as e:
            st.error(f"Error checking status: {e}")

        # 2. Predicted Revenue (Mock logic or from summary)
        st.subheader("Business Metrics")
        if os.path.exists(DAILY_BUSINESS_SUMMARY):
            try:
                df = pd.read_csv(DAILY_BUSINESS_SUMMARY)
                st.dataframe(df)
                
                # Example metric extraction
                if 'revenue' in df.columns:
                    total_revenue = df['revenue'].sum()
                    st.metric("Total Predicted Revenue", f"${total_revenue:,.2f}")
            except Exception as e:
                st.error(f"Error reading summary csv: {e}")
        else:
            st.info("No Daily Business Summary found yet.")
            
        # 3. Click Logs Viewer
        st.subheader("Recent Clicks")
        if os.path.exists(CLICK_LOG_FILE):
            try:
                clicks_df = pd.read_csv(CLICK_LOG_FILE)
                st.dataframe(clicks_df.tail(50)) # Show last 50
            except Exception as e:
                st.error(f"Error reading click logs: {e}")
        else:
            st.info("No clicks logged yet.")

    elif password:
        st.error("Incorrect Password")

# ================== MAIN APP LOGIC ==================
def main():
    st.set_page_config(page_title="Redirect Bridge & Dashboard", layout="wide")
    
    # Check if this is a redirect request
    if "url" in st.query_params:
        redirect_bridge()
    
    # Otherwise show dashboard
    admin_dashboard()

if __name__ == "__main__":
    main()
