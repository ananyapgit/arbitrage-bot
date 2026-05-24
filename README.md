# Arbitrage Deal Bot (Serverless Hardened)

![Serverless Status](https://img.shields.io/badge/Serverless-Active-brightgreen)

A high-frequency arbitrage deal bot designed for automated affiliate marketing with revenue intelligence, audit compliance, and fail-closed safety mechanisms. Now running in a **Hardened Serverless Architecture**.

## 🚀 Features

### Serverless & Security (New!)
- **GitHub Actions Scraper**: The scraping engine runs every 5 minutes on GitHub's infrastructure, completely removing the need for a local server.
- **Secret Management**: All credentials (API Keys, Affiliate Tags) are strictly managed via GitHub Secrets and Streamlit Secrets. No hardcoded tokens.
- **Streamlit Cloud Dashboard**: The Redirect Bridge and Admin Dashboard are hosted 24/7 on Streamlit Cloud.

### Phase 6+: Revenue Intelligence & Hardening
- **Redirect Bridge**: All outbound links are wrapped via a local bridge (`redirect_server.py`) for click tracking and affiliate tag injection.
- **Revenue Intelligence**: Real-time EPC (Earnings Per Click) calculation and category-level throttling.
- **Audit Compliance**:
    - `rejection_audit.log`: Logs every rejected deal with granular reasons (Trust, Price, OOS).
    - `config_change_log.csv`: Automatically tracks runtime configuration drift.
    - `daily_business_summary.csv`: Midnight summary of clicks, revenue, and performance.
- **Safety & Resilience**:
    - **Fail-Closed Design**: Network or logic failures stop the specific action without crashing the bot, but prevent unsafe posting.
    - **Spam Safety Pause**: Automatically pauses Telegram posting for 24h if flood limits are hit.
    - **Kill Switch**: Global kill switch support (`kill_switch.active`).
- **Shadow Mode**: Redirects posts to a private channel for validation.

### Super Bot Architecture (v1.3)
- Behavior Levers (no changes to monetization or trust thresholds):
  - Urgency: Low stock indicators append a lightweight tag and scarcity bar to increase action.
  - Personalization: Users can register a waitlist monitor (/monitor ASIN TargetPrice); alerts are delivered via DM only when price meets target.
  - Social Proof: Autonomous loop monitors click logs and escalates trending signals by editing live messages when interest surpasses thresholds.
  - Omnichannel: High-EPC categories (e.g., Electronics) cross-post to Discord; failures never block Telegram posting.

Operational Rules:
- Implementation first, validation second, documentation third.
- Missing data does not halt progress; unmet conditions are recorded as TODO/audit entries.
- Shadow testing validates behavior without redesigning core logic.

## How Revenue Emerges in This System
- Click-through rates (CTR) drive users to retailer pages via affiliate redirects. Some clicks convert to purchases, generating affiliate revenue.
- Urgency tags, social proof escalations, and personalized DMs increase the probability of clicking and buying, thereby improving EPC (earnings per click).
- Shadow testing validates behavioral lift (e.g., more clicks, faster engagement) while keeping monetization logic and trust thresholds unchanged; it does not directly measure revenue during shadow runs.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repo_url>
   cd Arbitrage
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure `aiohttp`, `pandas`, `python-telegram-bot`, `cachetools`, `python-dotenv` are installed)*

3. **Configuration**:
   - Create a `.env` file for local testing (see `config.py` for required variables).
   - For Production (GitHub Actions/Streamlit), use their respective Secrets management UI.

## 🏃‍♂️ Usage

### 1. Serverless Scraper (GitHub Actions)
The bot runs automatically every 5 minutes via `.github/workflows/main.yml`.
- **Trigger Manually**: Go to GitHub Actions -> Arbitrage Bot Runner -> Run Workflow.
- **Output**: Logs and data files (`deals.json`, `click_logs.csv`) are automatically committed back to the repo.

### 2. Streamlit Cloud (Redirect Bridge & Dashboard)
Host `app.py` on Streamlit Cloud.
- **Secrets Required**: `ADMIN_PASSWORD`, `BOT_TOKEN` (if needed for bot ops), `REDIRECT_BRIDGE_URL` (in config).
- **Access**: Visit your Streamlit App URL.

### 3. Local Testing
```bash
python main.py
```
This will run the bot in "Persistent Mode" (Infinite Loop) unless `GITHUB_ACTIONS=true` is set.

## 📊 Analytics & Logs

- **`daily_business_summary.csv`**: Daily high-level metrics (Revenue, Clicks, Best Category).
- **`click_logs.csv`**: Raw click stream data.
- **`rejection_audit.log`**: Audit trail for why deals were not posted.
- **`post_audit.log`**: Record of successful posts.
- **`config_change_log.csv`**: History of configuration changes.

## 🛡️ Safety Mechanisms

- **Config Drift**: The bot checks `config_change_log.csv` on startup. Silent config changes are logged.
- **Trust Decay**: Telegram errors increment a decay score in `trust_decay.json`. High decay triggers a pause.
- **Category Throttling**: Categories with EPC < $0.10 are automatically paused for 12 hours.

## 📜 Version History

- **v1.5-serverless**: Hardened Serverless Architecture with GitHub Actions and Streamlit Secrets.
- **v1.4-live-ready**: Hybrid Streamlit deployment, Async IO upgrade, Launch Validator.
- **v1.3-super-bot**: Urgency tags, Social Proof, Omnichannel.
- **v1.1-revenue-intelligence**: Added Redirect Bridge, EPC Engine, Audit Logging.
- **v1.0-prelaunch**: Initial Deal Engine & Scraper Logic.

See [CHANGELOG.md](CHANGELOG.md) for full details.
