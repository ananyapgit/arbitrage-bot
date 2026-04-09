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

# Glassmorphism Theme (Dark Mode) - High-Fidelity Clone
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
        color: white;
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
    /* FontAwesome Injection Simulation */
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css');
    .icon {
        font-size: 24px;
        margin-bottom: 10px;
        color: #00ff00;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper to load stats
def load_data():
    # Load from GitHub raw CSV for real-time data
    csv_url = "https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/master_log.csv"
    try:
        df = pd.read_csv(csv_url)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Rename columns to match existing dashboard expectations
        df = df.rename(columns={
            'timestamp': 'Timestamp',
            'discount_percentage': 'Discount%',
            'platform': 'Source'
        })
        return df
    except Exception as e:
        st.error(f"Failed to load data from GitHub: {e}")
        return pd.DataFrame()

def load_heartbeat():
    heartbeat_file = "heartbeat.json"
    if os.path.exists(heartbeat_file):
        try:
            with open(heartbeat_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"status": "🔴 Offline", "last_run": "Never"}

df = load_data()
heartbeat = load_heartbeat()

# Sidebar - System Logs & Status
with st.sidebar:
    st.markdown('### <i class="fas fa-bolt icon"></i> Real-Time Status', unsafe_allow_html=True)
    
    # Heartbeat Status
    last_run_str = heartbeat.get("last_run", "Never")
    
    if last_run_str == "Never":
        status_color = "🔴"
        last_sync_display = "Never"
        time_diff = 9999
    else:
        try:
            last_run_time = datetime.fromisoformat(last_run_str)
            time_diff = (datetime.now() - last_run_time).total_seconds() / 60
            status_color = "🟢" if time_diff < 10 else "🔴"
            last_sync_display = last_run_time.strftime('%H:%M:%S')
        except ValueError:
            status_color = "🔴"
            last_sync_display = "Error"
            time_diff = 9999

    st.markdown(f"**Status:** {status_color} {heartbeat.get('status', 'Offline')}")
    st.markdown(f"**Last Sync:** {last_sync_display}")
    
    st.divider()
    st.markdown('### <i class="fas fa-list icon"></i> System Logs', unsafe_allow_html=True)
    if os.path.exists("bot.log"):
        with open("bot.log", "r", encoding="utf-8", errors="ignore") as f:
            logs = f.readlines()[-10:]
            for log in reversed(logs):
                st.caption(log)
    else:
        st.caption("No logs available yet.")

# Main Dashboard
st.title("💎 Arbitrage Bot | Fintech Analytics")

if not df.empty:
    # Row 1: Volume Metrics (High-Fidelity Clone)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_deals = len(df)
        st.markdown(f'''
        <div class="metric-card">
            <i class="fas fa-database icon"></i><br>
            ### Total Revenue Links<br>
            <h2 id="dealCounter">{total_deals}</h2>
            <p>Live Deal Pipeline</p>
        </div>
        <script>
        // CountUp animation for deal counter
        function animateCounter() {{
            const counter = document.getElementById('dealCounter');
            if (counter) {{
                const target = {total_deals};
                let current = 0;
                const increment = target / 50;
                const timer = setInterval(() => {{
                    current += increment;
                    if (current >= target) {{
                        current = target;
                        clearInterval(timer);
                    }}
                    counter.textContent = Math.floor(current);
                }}, 30);
            }}
        }}
        // Run animation when page loads
        setTimeout(animateCounter, 500);
        </script>
        ''', unsafe_allow_html=True)
        
    with col2:
        last_24h = df[df['Timestamp'] > (datetime.now() - timedelta(hours=24))]
        st.markdown('<div class="metric-card"><i class="fas fa-chart-line icon"></i><br>### 24h Momentum<br><h2>' + str(len(last_24h)) + '</h2><p style="color:#00ff00">▲ Active Growth</p></div>', unsafe_allow_html=True)
        
    with col3:
        avg_savings = df['Discount%'].mean()
        st.markdown('<div class="metric-card"><i class="fas fa-tags icon"></i><br>### Avg. Savings<br><h2>' + f"{avg_savings:.1f}%" + '</h2><p>High-Value Filter</p></div>', unsafe_allow_html=True)
        
    with col4:
        success_rate = (df['ScraperStatus'] == "200 OK").mean() * 100
        st.markdown('<div class="metric-card"><i class="fas fa-shield-halved icon"></i><br>### Stealth Status<br><h2>' + f"{success_rate:.1f}%" + '</h2><p>2026 Bypass Active</p></div>', unsafe_allow_html=True)

    # Row 2: Radar Chart (Professional Grade)
    st.divider()
    col_chart1, col_chart2 = st.columns([1, 1])
    
    with col_chart1:
        st.markdown("### <i class='fas fa-chart-pie icon'></i> Category Deal Velocity", unsafe_allow_html=True)
        # Radar Chart Logic - Use category distribution from CSV with diverse categories
        if 'category' in df.columns:
            cat_counts = df['category'].value_counts().reset_index()
            cat_counts.columns = ['category', 'count']
            
            # Ensure diverse categories are displayed
            category_mapping = {
                'general': 'General',
                'audio': 'Audio', 
                'laptop': 'Laptops',
                'fashion': 'Fashion',
                'beauty': 'Beauty',
                'home': 'Home & Kitchen',
                'electronics': 'Electronics',
                'accessory': 'Accessories'
            }
            
            # Map categories to display names
            cat_counts['category'] = cat_counts['category'].map(category_mapping).fillna(cat_counts['category'])
            
            fig_radar = px.line_polar(cat_counts, r='count', theta='category', line_close=True,
                                    title="Deal Distribution by Category")
            fig_radar.update_traces(fill='toself')
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, cat_counts['count'].max() if len(cat_counts) > 0 else 10])
                )
            )
        else:
            # Fallback to Source if category not available
            cat_counts = df['Source'].value_counts().reset_index()
            fig_radar = px.line_polar(cat_counts, r='count', theta='Source', line_close=True)
        fig_radar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "white"},
            polar=dict(bgcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        
    with col_chart2:
        st.markdown("### <i class='fas fa-gauge icon'></i> Scraper Success Rate", unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = success_rate,
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#00ff00"},
                'steps' : [
                    {'range': [0, 50], 'color': "rgba(255, 0, 0, 0.3)"},
                    {'range': [50, 80], 'color': "rgba(255, 255, 0, 0.3)"}],
                'threshold' : {
                    'line': {'color': "white", 'width': 4},
                    'thickness': 0.75,
                    'value': 90}}))
        fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)

    # Row 3: Live Dataframe
    st.divider()
    st.markdown("### <i class='fas fa-satellite-dish icon'></i> Live Deal Stream (Last 15)", unsafe_allow_html=True)
    
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
    st.info("The dashboard will auto-refresh once data/master_log.csv is generated.")
