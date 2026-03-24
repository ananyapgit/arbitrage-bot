import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import os
import json
from datetime import datetime, timedelta

# Page Config
st.set_page_config(
    page_title="Arbitrage Bot High-Fidelity Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-refresh every 60 seconds
st_autorefresh(interval=60000, key="datarefresh")

# Glassmorphism Theme (Dark Mode)
st.markdown("""
    <style>
    .main {
        background: #0e1117;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #1c1f26 100%);
    }
    .sidebar .sidebar-content {
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(20px);
    }
    </style>
    """, unsafe_allow_html=True)

# Helper to load stats
def load_data():
    stats_file = "data/stats.csv"
    if os.path.exists(stats_file):
        df = pd.read_csv(stats_file)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    return pd.DataFrame()

def load_heartbeat():
    heartbeat_file = "heartbeat.json"
    if os.path.exists(heartbeat_file):
        with open(heartbeat_file, 'r') as f:
            return json.load(f)
    return {"status": "🔴 Offline", "last_run": "Never"}

df = load_data()
heartbeat = load_heartbeat()

# Sidebar - System Logs & Status
with st.sidebar:
    st.title("⚡ System Heartbeat")
    
    # Heartbeat Status
    last_run_time = datetime.fromisoformat(heartbeat.get("last_run", datetime.now().isoformat()))
    time_diff = (datetime.now() - last_run_time).total_seconds() / 60
    
    status_color = "🟢" if time_diff < 10 else "🔴"
    st.markdown(f"**Status:** {status_color} {heartbeat.get('status', 'Offline')}")
    st.markdown(f"**Last Sync:** {last_run_time.strftime('%H:%M:%S')}")
    
    st.divider()
    st.markdown("### 📜 System Logs")
    if os.path.exists("bot.log"):
        with open("bot.log", "r") as f:
            logs = f.readlines()[-10:]
            for log in reversed(logs):
                st.caption(log)
    else:
        st.caption("No logs available yet.")

# Main Dashboard
st.title("💎 Arbitrage Bot | Professional Analytics")

if not df.empty:
    # Row 1: Volume Metrics (Impressive Section)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Total Deals")
        st.markdown(f"## {len(df)}")
        st.caption("Lifetime Deals Sent")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        last_24h = df[df['Timestamp'] > (datetime.now() - timedelta(hours=24))]
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📈 24h Momentum")
        st.markdown(f"## {len(last_24h)}")
        st.markdown('<span style="color:#00ff00">▲ Active Growth</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        avg_savings = df['Discount%'].mean()
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 💰 Avg. Savings")
        st.markdown(f"## {avg_savings:.1f}%")
        st.caption("High-Value Filtering")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col4:
        success_rate = (df['ScraperStatus'] == "200 OK").mean() * 100
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 🛡️ Stealth Health")
        st.markdown(f"## {success_rate:.1f}%")
        st.caption("2026 Bypass Active")
        st.markdown('</div>', unsafe_allow_html=True)

    # Row 2: Charts
    st.divider()
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        st.markdown("### 📉 Scraper Health Gauge")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = success_rate,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Success Rate %"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#00ff00"},
                'steps' : [
                    {'range': [0, 50], 'color': "gray"},
                    {'range': [50, 80], 'color': "lightgray"}],
                'threshold' : {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90}}))
        fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)
        
    with col_chart2:
        st.markdown("### 🕸️ Category Velocity")
        # Sample data for radar if categories aren't rich yet
        categories = df['Source'].value_counts().reset_index()
        fig_radar = px.line_polar(categories, r='count', theta='Source', line_close=True)
        fig_radar.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, polar=dict(bgcolor='rgba(255,255,255,0.05)'))
        st.plotly_chart(fig_radar, use_container_width=True)

    # Row 3: Live Dataframe
    st.divider()
    st.markdown("### 🛰️ Live Deal Stream (Last 15)")
    
    display_df = df.sort_values(by='Timestamp', ascending=False).head(15)
    st.dataframe(
        display_df,
        column_config={
            "Timestamp": st.column_config.DatetimeColumn("Time"),
            "Discount%": st.column_config.NumberColumn("Savings", format="%.2f%%"),
            "Price": "Offer Price"
        },
        hide_index=True,
        use_container_width=True
    )
    
else:
    st.warning("Waiting for the first 5-minute loop to complete... 🚀")
    st.info("The dashboard will auto-refresh once data/stats.csv is generated.")
