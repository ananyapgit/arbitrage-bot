# Technical Audit: Security & Architecture

## Security Model: Secrets & Scoped Permissions

### 1. Secret Management
We have migrated from hardcoded credentials to a strict environment-variable-based security model.

**Local Development:**
- Secrets are loaded from a `.env` file (which is git-ignored).
- `python-dotenv` handles the loading mechanism in `config.py` and `main.py`.

**Production (Serverless/GitHub Actions):**
- Secrets are injected via GitHub Actions Secrets.
- No sensitive data is written to disk or committed to the repository.

**Required Secrets:**
- `BOT_TOKEN`: Telegram Bot API Token.
- `TELEGRAM_CHAT_ID`: The target channel ID.
- `AMAZON_TAG`: Amazon Affiliate Tag.
- `FLIPKART_TAG`: Flipkart Affiliate Tag.
- `REDIRECT_BRIDGE_URL`: URL of the Streamlit Redirect Bridge.
- `ADMIN_PASSWORD`: Password for the Streamlit Dashboard (set in Streamlit Cloud Secrets).

### 2. Streamlit Cloud Security
- `app.py` uses `st.secrets` to access `ADMIN_PASSWORD`.
- Streamlit Cloud manages these secrets securely, injecting them at runtime.

### 3. GitHub Actions Permissions
- The `stefanzweifel/git-auto-commit-action` requires `contents: write` permission (default in standard tokens) to push updated logs back to the repo.
- The cron job runs in an ephemeral runner, ensuring no state persistence beyond the committed artifacts.

## Architecture: Hybrid Serverless

### Components
1.  **Scraper Engine (GitHub Actions)**:
    - Triggers every 60 minutes.
    - Runs a single scrape/post cycle (`main.py` -> `bot.deal_engine(single_run=True)`).
    - Commits state (cache, logs) back to the repo to maintain continuity.

2.  **Redirect Bridge & Dashboard (Streamlit Cloud)**:
    - Hosted permanently on Streamlit.
    - Handles `redirect_server` logic via `app.py`.
    - Provides Admin UI.

### Data Flow
1.  Scraper finds deal -> Posts to Telegram with Redirect Bridge URL.
2.  User clicks link -> Redirect Bridge logs click -> Redirects to Retailer.
3.  Scraper run finishes -> Commits `deals.json` and logs to Repo.
4.  Dashboard reads committed logs from Repo (via file system or raw URL if extended).

## Fail-Safe Mechanisms
- **GitHub Actions Timeout**: Jobs are limited by default, preventing stuck loops.
- **Fail-Closed Config**: If secrets are missing, `config.py` logic prevents the bot from starting in a broken state.
- **Artifact Persistence**: Critical business data (clicks, cache) is versioned via Git.
