# Logging Contract

## Log Files

- bot_log.txt: high-level runtime logs and warnings.
- rejection_audit.log: structured records of rejected deals.
- post_audit.log: records of successfully posted deals.
- enrichment_log: enrichment and network failure taxonomy evidence.
- failure_test_execution_log.csv: failure taxonomy test executions.
- resilience_shadow_chaos_testing_log.csv: shadow and chaos test results.
- config_change_log.csv: configuration drift and mutation history.
- launch_validation_report.json: aggregated launch validation results.

## Rejection Audit Schema

- timestamp: ISO-8601 timestamp of the rejection event.
- deal_identifier: URL or ASIN used to identify the deal.
- reason: stage label and detail string.
- source: subsystem that recorded the rejection.

## When Files Must Exist

- rejection_audit.log: when any enrichment or validation rejection occurs.
- failure_test_execution_log.csv: after running failure taxonomy tests.
- resilience_shadow_chaos_testing_log.csv: after running shadow chaos tests.
- config_change_log.csv: whenever configuration values are mutated or drift.
- launch_validation_report.json: after running the launch validator.

## Fatal vs Non-Fatal Absence

- Fatal: missing rejection_audit.log when a failure taxonomy test expects it.
- Fatal: missing config_change_log.csv during launch validation.
- Non-fatal: missing bot_log.txt or post_audit.log before first run.
- Non-fatal: missing resilience logs before chaos tests are executed.


Last Auto-Update: 2026-01-14T18:21:09+00:00
