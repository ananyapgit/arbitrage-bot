# System Architecture

## Overview
The Arbitrage Bot is a **Serverless, Async, Event-Driven** system designed for high-speed deal discovery, affiliate revenue generation, and automated compliance. It operates on a "Pulse" model using GitHub Actions for execution and a hosted Redirect Bridge for link security.

## High-Level Diagram

```mermaid
graph TD
    A[GitHub Actions (Cron: 10m)] -->|Trigger| B(Bot Runner)
    B -->|Load State| C{State Files}
    C -->|deals.json, cache.json| B
    
    B -->|Async Scrape| D[Scrapers]
    D -->|Amazon, Flipkart| E(External Sites)
    
    B -->|Enrich & Filter| F[Deal Engine]
    F -->|Fail-Closed Checks| G{Validation}
    G -->|Fail| H[rejection_audit.log]
    G -->|Pass| I[Telegram Post]
    
    I -->|Link with Bridge| J[User Clicks]
    J -->|HTTPS| K[Redirect Bridge (Render)]
    K -->|Log Click| L[click_logs.csv]
    K -->|Cleanse & Redirect| M(Amazon Product Page)
    
    B -->|Commit State| C
```

## Core Components

### 1. Bot Runner (`main.py`, `bot.py`)
- **Role**: Orchestrator.
- **Tech**: Python 3.10, `asyncio`.
- **Logic**: 
    - Checks `GITHUB_ACTIONS` env to determine mode (Serverless vs Loop).
    - Runs `deal_engine` to fetch, validate, and post deals.
    - Manages "Pulse" logic: Start -> Load State -> Execute -> Save State -> Exit.

### 2. Scrapers (`scrapers/`)
- **Role**: Data Ingestion.
- **Tech**: `aiohttp`, `BeautifulSoup`.
- **Features**:
    - **Async/Concurrent**: Uses `asyncio.gather` for parallel fetching.
    - **Scarcity Logic**: Detects "Only X left" or ">70% off" to trigger `🚨 LOOT ALERT`.
    - **Resilience**: Retries with exponential backoff on network errors.

### 3. Deal Engine (`deal_engine.py`)
- **Role**: Business Logic & Validation.
- **Features**:
    - **Fail-Closed**: Any missing data (Price, Title) results in rejection.
    - **Trust Safety**: Checks Seller Rating, Shipping Cost.
    - **Revenue Protection**: Ensures Anchor Price > New Price.

### 4. Redirect Bridge (`redirect-service/index.js`)
- **Role**: Link Security & Analytics.
- **Tech**: Node.js, Express (Hosted on Render).
- **Features**:
    - **Link Cleansing**: Extracts ASIN, strips third-party tags, appends `AMAZON_TAG`.
    - **Click Logging**: Captures User ID, Platform, Timestamp (via `redirect_server.py` or future integration).
    - **Hijack Prevention**: Prevents affiliate tag injection by malicious actors.

### 5. Audit Dashboard (`app.py`)
- **Role**: Observability.
- **Tech**: Streamlit.
- **Features**:
    - **Revenue Projection**: Real-time charts of potential earnings.
    - **System Health**: Visual status of Scrapers and Failure Taxonomy compliance.
    - **Logs**: Viewable `click_logs.csv` and `rejection_audit.log`.

## Deployment Strategy
- **Compute**: GitHub Actions (Free Tier compatible, scalable).
- **Storage**: Git Repo (State files committed automatically).
- **Bridge**: Render (Free/Starter Web Service).
- **Secrets**: GitHub Secrets / `.env` (Zero hardcoded keys).
