# Technical Audit & Compliance Report

## 1. System Integrity & Security

### Fail-Closed Design Pattern (FT-010)
The system implements a strict "Fail-Closed" architecture to prevent revenue leakage and hijack attempts.
- **Mechanism**: If any critical enrichment step (Price Check, Stock Check, Affiliate Tagging) fails, the deal is **rejected immediately**.
- **Bridge Security**: The Redirect Bridge (`redirect-service`) validates all incoming URLs. If a URL cannot be parsed or cleansed of third-party tags, the redirect is aborted (returns 400 or logs error), ensuring no "open redirect" vulnerability exists.
- **Logging**: All rejections are logged to `rejection_audit.log` with structured codes (e.g., `rating_below_threshold`, `missing_critical_fields`).

### Hijack-Safe Affiliate Plumbing
- **ASIN-Level Cleansing**: The bridge extracts the ASIN from the target URL and reconstructs a clean Amazon URL with *only* the authorized Affiliate Tag (`AMAZON_TAG`).
- **Tag Stripping**: Any existing `tag`, `linkCode`, or `ascsubtag` parameters from the source URL are stripped before redirection.
- **Environment Isolation**: Affiliate tags are injected via environment variables (`AMAZON_TAG`, `FLIPKART_TAG`), never hardcoded, preventing accidental exposure or unauthorized modification.

## 2. Serverless State Persistence

### Stateless Execution Model
The bot operates as a "Pulse" function via GitHub Actions (`bot_runner.yml`), triggering every 10 minutes. It does not rely on long-running server processes.

### Persistence Strategy
To maintain continuity across ephemeral runs, the system uses a Git-based persistence layer:
1.  **State Loading**: At startup, the bot loads `click_logs.csv`, `deals.json`, `trust_decay.json`, and `sale_followup_cache.json` from the repository.
2.  **Processing**: The bot processes new deals, updates caches (e.g., "seen deals", "follow-up timestamps"), and logs clicks.
3.  **State Committing**: At the end of the run, `git-auto-commit-action` commits the updated state files back to the repository.
4.  **Conflict Resolution**: Short cycle times (10m) and single-threaded execution reduce race conditions.

## 3. Failure Taxonomy (FT) Compliance

| FT Code | Description | Handling Strategy | Status |
| :--- | :--- | :--- | :--- |
| **FT-001** | API Timeout | Exponential Backoff (1s, 2s, 4s) -> Reject | ✅ PASS |
| **FT-002** | Schema Change | HTML Parsing Exception -> Log -> Reject | ✅ PASS |
| **FT-003** | Rate Limit | 429 Detection -> Pause Execution -> Log | ✅ PASS |
| **FT-004** | Empty Feed | Feed Validation Check -> Warn -> Retry | ✅ PASS |
| **FT-005** | Auth Fail | Environment Variable Check -> System Exit(1) | ✅ PASS |
| **FT-010** | Hijack Attempt | Bridge URL Cleansing -> Strip Tags -> Redirect | ✅ PASS |
| **FT-016** | Trust Decay | High Failure Rate -> Cooldown User/Channel | ✅ PASS |

## 4. Revenue & Audit Trail
- **Click Logging**: Every click is logged to `click_logs.csv` with Timestamp, User ID, Category, and Platform.
- **Revenue Projection**: `app.py` calculates projected revenue based on `Clicks * 1% Conversion * 5% Commission`.
- **Audit Logs**: `rejection_audit.log` provides a full trail of why deals were not posted, satisfying "Audit-Proof Analytics".
