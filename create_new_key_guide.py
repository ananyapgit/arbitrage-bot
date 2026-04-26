#!/usr/bin/env python3
"""
Guide to create a new API key that definitely works
"""

print("🔧 CREATE NEW SENDGRID API KEY GUIDE")
print("=" * 50)

print("""
🚨 SOLUTION: Create New API Key with Full Access

The permission update might have a delay. Let's create a fresh API key:

STEP 1: Create New API Key
1. Go to: https://app.sendgrid.com/settings/api_keys
2. Click "Create API Key"
3. Name: "Arbitrage Bot Full Access"
4. API Key Permission: ✅ "Full Access" (this includes mail send)
5. Click "Create & View"

STEP 2: Copy New API Key
- Copy the new API key (it will start with "SG.")
- Keep it safe

STEP 3: Update GitHub Secrets
1. Go to your repository
2. Settings → Secrets and variables → Actions
3. Update SENDGRID_API_KEY with the new key
4. Keep SENDGRID_FROM_EMAIL as "ananyap.workmail@gmail.com"

STEP 4: Test the New Key
Run this test with your new API key:

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Set your new API key
os.environ["SENDGRID_API_KEY"] = "YOUR_NEW_FULL_ACCESS_KEY"
os.environ["SENDGRID_FROM_EMAIL"] = "ananyap.workmail@gmail.com"

from sendgrid_notifier import SendGridNotifier

notifier = SendGridNotifier()
test_deal = {
    "id": "test-123",
    "title": "Test Deal - New API Key",
    "price": "₹999",
    "original_price": "₹1999", 
    "affiliate_url": "https://amazon.in/test/dp/B123456789",
    "source": "test",
    "category": "test"
}

sent = notifier.broadcast_loot_deal(test_deal, 50.0)
print(f"✅ Success! Sent {sent} emails" if sent > 0 else "❌ Still failing")

WHY FULL ACCESS?
- "Full Access" ensures all permissions including mail send
- Avoids permission propagation delays
- Guarantees the API key can send emails

ALTERNATIVE: Verify Sender Email
If still failing, verify your sender:
1. SendGrid → Settings → Sender Authentication
2. Verify "ananyap.workmail@gmail.com" as single sender
3. Or verify your domain "workmail.com"

Once you create the new API key with Full Access, 
the GitHub workflow will work immediately! 🚀
""")
