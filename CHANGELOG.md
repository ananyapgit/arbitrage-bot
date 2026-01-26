# Changelog

## v1.3-superbot-upgrade
- Added stock & urgency engine: extracts low stock/percent claimed and appends concise urgency tag once.
- Implemented waitlist monitor system with /monitor command handler stub and DM-only alerts.
- Introduced social proof loop: edits live Telegram messages when click interest spikes; prevents repeated escalations.
- Activated omnichannel deployment to Discord for high-EPC categories; Discord errors do not block Telegram.
- Expanded daily_business_summary.csv with personalization, urgency, social-proof counters.
- Enhanced rejection_audit.log with actual seller rating value for TRUST_RATING_THRESHOLD rejections.
- Documentation updated: README Super Bot section; Behavioral Systems explained.

All notable changes to the Arbitrage Deal Bot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1-revenue-intelligence] - 2026-01-10

### Added
- **Revenue Intelligence Bridge**: `redirect_server.py` now handles all outbound clicks with non-blocking logging and affiliate tag injection.
- **Config Drift Detection**: `config_monitor.py` automatically detects and logs any runtime configuration changes to `config_change_log.csv`.
- **Rejection Audit Logging**: All rejected deals are now logged to `rejection_audit.log` with granular reasons (Trust, Price, OOS, Network).
- **Trust Decay System**: `trust_decay.json` tracks Telegram Forbidden/Spam events to trigger auto-pause logic.
- **Daily Business Summary**: `analytics_engine.py` now generates a midnight summary including "Deals Rejected vs Posted" and EPC calculations.
- **Category Throttling**: Automated logic to pause categories with EPC < $0.10 for 12 hours.
- **Failure Taxonomy Tests**: Added FT-RI-01 to FT-RI-05 covering Redirect Bridge failure modes.
- **Master Test Runner**: `run_all_tests.py` to execute all validation suites.

### Changed
- **Bot Core (`bot.py`)**:
    - Integrated `config_monitor` startup check.
    - Added `log_rejection` calls to all validation failure points.
    - Added `log_post` calls for successful posts.
    - Updated `post_to_telegram` to feed `trust_decay.json` on errors.
    - Added `check_category_throttle` logic to the main deal loop.
- **Analytics Engine**: Updated to consume `post_audit.log` and `rejection_audit.log` for comprehensive reporting.

### Security
- **Shadow Mode**: Enforced strict Shadow Mode redirects for all Telegram posts in test environments.
- **Fail-Closed Design**: Network errors, config drift, and throttling logic now default to safety (stop/log) rather than unsafe operation.

## [v1.0-prelaunch] - 2026-01-08

### Added
- Initial Release of Arbitrage Deal Bot.
- Core `deal_engine` with multi-scraper support.
- `bot.py` with async Telegram/Discord posting.
- Basic Failure Taxonomy (FT-001 to FT-016).
- Shadow Mode configuration.
