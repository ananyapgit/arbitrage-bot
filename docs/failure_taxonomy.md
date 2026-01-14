# Failure Taxonomy

## Failure Layers

- Network: DNS errors, timeouts, connection resets, SSL issues.
- HTTP: non-success status codes and malformed responses.
- Schema: structural payload issues and type mismatches.
- Data: missing or malformed business fields such as title and price.
- Config: invalid, missing, or drifting configuration values.
- Trust: seller quality and hidden cost checks.
- Buyability: ability to successfully purchase the item.
- Revenue: monetization and EPC-related gating.
- Redirect: affiliate redirect and bridge handling.
- Platform: Telegram API and chat-level issues.
- Time: time-based validation and scheduling problems.
- Deal engine: batch processing and deduplication logic.

## Precedence Rules

- Network and HTTP failures are evaluated before anything else.
- Schema and data validation run before trust and buyability.
- Trust checks run before buyability and revenue.
- Buyability checks run before revenue and redirect logic.
- Redirect and platform issues are evaluated at posting time.
- The first failure that fires becomes the single recorded reason for a deal.
- A deal must not accumulate multiple competing failure reasons.

## Example Logs

- Network Failure | http_500
- Schema Failure | missing_url
- Data Failure | missing_critical_fields
- Trust Failure | rating_below_threshold
- Trust Failure | shipping_too_high
- Buyability Failure | price_out_of_bounds
- Buyability Failure | out_of_stock
- Buyability Failure | no_buy_button
- Revenue Failure | missing_anchor_pricing
- Redirect Failure | missing_target_url

Last Auto-Update: 2026-01-14T18:21:09+00:00

Auto-Update Summary: 2026-01-14T18:21:09+00:00
- Tests: 116 passed / 0 failed / 116 total
- Blockers: 0
- Artifacts: rejection_audit.log=1560B, failure_test_execution_log.csv=332088B, launch_validation_report.json=42823B
- Config Change Log: 2631B
