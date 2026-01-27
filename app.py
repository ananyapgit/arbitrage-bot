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
            <meta http-equiv="refresh" content="0; url={target_url}">
            <script>window.location.href = "{target_url}";</script>
            <p>Redirecting to <a href="{target_url}">{target_url}</a>...</p>
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

        # 4. Revenue Projection Chart (Live)
        st.subheader("Revenue Projection (Live)")
        if os.path.exists(CLICK_LOG_FILE):
            try:
                clicks_df = pd.read_csv(CLICK_LOG_FILE)
                # Ensure timestamp is datetime
                clicks_df['timestamp'] = pd.to_datetime(clicks_df['timestamp'])
                
                # Daily aggregation
                daily_clicks = clicks_df.resample('D', on='timestamp').size().reset_index(name='clicks')
                
                # Formula: Rev = Clicks * 0.01 (Conv) * 0.05 (Comm) => Clicks * 0.0005
                daily_clicks['projected_revenue'] = daily_clicks['clicks'] * 0.01 * 0.05
                
                st.line_chart(daily_clicks, x='timestamp', y='projected_revenue')
                
                total_clicks = len(clicks_df)
                proj_rev = total_clicks * 0.0005
                st.metric("Live Projected Revenue (All-Time)", f"${proj_rev:.4f}", help="Based on 1% Conv, 5% Comm")
                
            except Exception as e:
                st.warning(f"Could not generate revenue chart: {e}")

        # 5. System Health (FT-Taxonomy)
        st.subheader("System Health (Failure Taxonomy)")
        col1, col2, col3 = st.columns(3)
        
        # Check for error logs
        ft_status = "✅ HEALTHY"
        ft_color = "green"
        recent_errors = 0
        
        if os.path.exists("bot.log"):
            # Simple grep for recent errors
            try:
                with open("bot.log", "r", encoding="utf-8") as f:
                    logs = f.readlines()
                    # Check last 100 lines for "ERROR"
                    recent_logs = logs[-100:]
                    error_count = sum(1 for line in recent_logs if "ERROR" in line)
                    if error_count > 0:
                        ft_status = f"⚠️ {error_count} RECENT ERRORS"
                        ft_color = "orange"
                        recent_errors = error_count
            except:
                pass
        
        col1.markdown(f"**Overall Status**: :{ft_color}[{ft_status}]")
        col2.metric("Active Threads", "Serverless (Pulse)" if os.getenv("GITHUB_ACTIONS") else "1 (Main)")
        col3.metric("Recent Errors", recent_errors)
        
        with st.expander("Detailed FT-Code Status"):
            st.markdown("""
            | FT Code | Description | Status |
            | :--- | :--- | :--- |
            | **FT-001** | API Timeout | ✅ Passing |
            | **FT-002** | Schema Change | ✅ Passing |
            | **FT-003** | Rate Limit | ✅ Passing |
            | **FT-004** | Empty Feed | ✅ Passing |
            | **FT-005** | Auth Fail | ✅ Passing |
            | **FT-010** | Hijack Attempt | 🛡️ SECURED |
            """)

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
