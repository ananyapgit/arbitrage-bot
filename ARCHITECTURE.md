# System Architecture

## Components

- Scrapers: fetch raw deals from retailers and content sources.
- Enrichment: normalize, validate, and enrich deals inside bot.py.
- Deal engine: batch selection, persona curation, throttling, and reciprocity.
- Posting: Telegram and Discord posting pipeline with caption generation.
- Revenue: affiliate tagging, redirect bridge, and analytics tracking.
- Validation: failure taxonomy tests, chaos tests, and launch validator.
 - Behavioral Systems:
   - Urgency: Low-stock detection appends concise tags and scarcity bars; enforced once per deal.
   - Personalization: Waitlist monitor (/monitor ASIN TargetPrice) persists to waitlist_db and triggers DM-only alerts when price meets target.
   - Social Proof: Analytics loop monitors click_logs and escalates trending signals via message edits; avoids repeated edits per threshold.

## Data Flow

- Scrapers emit deal payloads with URL, prices, and metadata.
- Enrichment fetches product pages, applies trust and buyability checks.
- Valid deals enter the deal engine for batching and prioritization.
- Revenue layer decorates links with affiliate tags and optional redirect bridge.
- Posting layer sends captions and links to Telegram and Discord.
- Logs and audits capture posts, rejections, clicks, and config changes.

## Failure Precedence

- Network and HTTP failures are handled first and fail closed.
- Schema and data validation enforce basic payload integrity.
- Trust checks apply rating and shipping thresholds for seller quality.
- Buyability checks enforce title, price, stock, and buy button presence.
- Revenue checks guard anchor pricing, discount sanity, and EPC throttling.
- First failing stage wins and is logged as the canonical rejection reason.

## Revenue Path

- Affiliate tags are added per marketplace and persona where applicable.
- Optional redirect bridge wraps outbound URLs for tracking and routing.
- Analytics engine consumes logs and click data for EPC and revenue metrics.

## Where Deals Die

- Network or HTTP unrecoverable errors during enrichment.
- Schema or data violations such as missing URL or malformed price.
- Trust violations from low seller rating or excessive shipping cost.
- Buyability failures such as missing title, invalid price, or out of stock.
- Revenue filters such as invalid anchor pricing or low effective discount.


Last Auto-Update: 2026-01-14T18:21:09+00:00
