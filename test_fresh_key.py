#!/usr/bin/env python3
"""
Test fresh API key - replace YOUR_NEW_KEY_HERE
"""
import os
from sendgrid_notifier import SendGridNotifier

# Use the API key from environment variables
# os.environ["SENDGRID_API_KEY"] = os.getenv("SENDGRID_API_KEY", "")
os.environ["SENDGRID_FROM_EMAIL"] = "ananyap.workmail@gmail.com"

print("🧪 Testing Fresh API Key...")
print("=" * 40)

notifier = SendGridNotifier()
test_deal = {
    "id": "test-123",
    "title": "Test Deal - Fresh API Key",
    "price": "₹999",
    "original_price": "₹1999", 
    "affiliate_url": "https://amazon.in/test/dp/B123456789",
    "source": "test",
    "category": "test"
}

try:
    sent = notifier.broadcast_loot_deal(test_deal, 50.0)
    if sent > 0:
        print(f"🎉 SUCCESS! Sent {sent} emails")
        print("✅ Ready for GitHub workflow!")
        print("🔧 Update GitHub secrets with this key")
    else:
        print("❌ Still failing - check sender verification")
except Exception as e:
    print(f"❌ Error: {e}")

# Instructions:
# 1. Create new API key with Full Access
# 2. Replace YOUR_NEW_KEY_HERE above
# 3. Run this script
# 4. If successful, update GitHub secrets
# 5. GitHub workflow will work immediately
