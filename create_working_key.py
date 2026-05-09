#!/usr/bin/env python3
"""
Create a working SendGrid API key step by step
"""

print("🔧 CREATE WORKING SENDGRID API KEY")
print("=" * 50)

print("""
🚨 IMMEDIATE ACTION REQUIRED:

The current API key SG.REDACTED
is still returning 401 even with Full Access.

STEP 1: Create BRAND NEW API Key
1. Go to: https://app.sendgrid.com/settings/api_keys
2. Click "Create API Key" 
3. Name: "Arbitrage Bot Working Key"
4. API Key Permission: ✅ "Full Access"
5. Click "Create & View"
6. COPY THE NEW KEY IMMEDIATELY

STEP 2: Test the New Key
Replace NEW_KEY_HERE with your fresh key and run:

import os
from sendgrid_notifier import SendGridNotifier

os.environ["SENDGRID_API_KEY"] = "NEW_KEY_HERE"
os.environ["SENDGRID_FROM_EMAIL"] = "ananyap.workmail@gmail.com"

notifier = SendGridNotifier()
test_deal = {
    "id": "test-123",
    "title": "Test Deal - Working Key",
    "price": "₹999",
    "original_price": "₹1999", 
    "affiliate_url": "https://amazon.in/test/dp/B123456789",
    "source": "test",
    "category": "test"
}

sent = notifier.broadcast_loot_deal(test_deal, 50.0)
print(f"✅ SUCCESS! Sent {sent} emails" if sent > 0 else "❌ Still failing")

STEP 3: Update GitHub Secrets
If the test succeeds:
1. Go to repository → Settings → Secrets and variables → Actions
2. Update SENDGRID_API_KEY with the working key
3. GitHub workflow will work immediately

STEP 4: Monitor GitHub Workflow
The current workflow should show debug output soon.
Check: https://github.com/ananyapgit/arbitrage-bot/actions

WHY THIS HAPPENS:
- SendGrid API keys can have propagation delays
- Sometimes keys get "stuck" with wrong permissions
- Fresh keys with Full Access work immediately

The GitHub workflow debug output will confirm if the new key works.
""")
