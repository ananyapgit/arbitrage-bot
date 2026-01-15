# Arbitrage Deal Bot (v1.3 Super Bot Upgrade)

A high-frequency arbitrage deal bot designed for automated affiliate marketing with revenue intelligence, audit compliance, and fail-closed safety mechanisms.

## 🚀 Features

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
   *(Note: Ensure `aiohttp`, `pandas`, `python-telegram-bot`, `cachetools` are installed)*

3. **Configuration**:
   - Edit `config.py` to set `BOT_TOKEN`, `CHANNELS`, and `AFFILIATE_TAGS`.
   - Ensure `REDIRECT_BRIDGE_URL` is set to your bridge endpoint (default: `http://localhost:8080/r`).

## 🏃‍♂️ Usage

### Start the Redirect Bridge (Required for Tracking)
```bash
python redirect_server.py
```

### Start the Bot
```bash
python bot.py
```

### Run Validation Tests
```bash
python run_all_tests.py
```
*Runs Failure Taxonomy, Redirect, and Shadow/Chaos test suites.*

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

- **v1.1-revenue-intelligence**: Added Redirect Bridge, EPC Engine, Audit Logging.
- **v1.0-prelaunch**: Initial Deal Engine & Scraper Logic.

See [CHANGELOG.md](CHANGELOG.md) for full details.
