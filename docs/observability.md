# Observability Guide

## Deal Lifecycle
- Scrape → Enrich/Validate → Post Decision → Post → Follow-up/Edits → Clicks/Revenue Analytics → Summary

## Metrics and Their Logs
- Deals scraped: post decisions and posted deals tracked in post_audit.log; enrichment outcomes recorded in rejection_audit.log
- Deals rejected (with reasons): rejection_audit.log (stage and detail)
- Deals posted: post_audit.log (timestamp, deal_identifier, category, platform)
- Clicks (redirect logs): click_logs.csv (timestamp, user_id, category, platform, target_url)
- Social proof escalations: social_proof_state.json (thresholds applied per URL)
- Personalized DMs: waitlist_db.json (entries with alerted=true and alerted_at)

## Questions and Where to Find Answers
- Did this make money?
  - daily_business_summary.csv (predicted_revenue, epc_per_category) and downstream affiliate dashboards
- Did users click?
  - click_logs.csv (per-URL and per-category counts) and daily_business_summary.csv (total_clicks, unique_users)
- Why was this deal rejected?
  - rejection_audit.log (canonical failure stage and detail string)
- Which behavior lever fired?
  - Urgency: presence of “[🔥 LOW STOCK …]” in titles and follow-up cache
  - Social Proof: social_proof_state.json entries for URLs
  - Personalization: waitlist_db.json entries with alerted=true

