#!/usr/bin/env python3
"""
Test new API key template - just replace the key
"""
import os
from sendgrid_notifier import SendGridNotifier

# Replace YOUR_NEW_API_KEY_HERE with your fresh API key
os.environ["SENDGRID_API_KEY"] = "YOUR_NEW_API_KEY_HERE"
os.environ["SENDGRID_FROM_EMAIL"] = "ananyap.workmail@gmail.com"

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

print("🧪 Testing Fresh API Key...")
try:
    sent = notifier.broadcast_loot_deal(test_deal, 50.0)
    if sent > 0:
        print(f"🎉 SUCCESS! Sent {sent} emails")
        print("✅ Ready to update GitHub secrets!")
    else:
        print("❌ Still failing")
except Exception as e:
    print(f"❌ Error: {e}")

# Instructions:
# 1. Replace YOUR_NEW_API_KEY_HERE with your new key
# 2. Run this script
# 3. If successful, update GitHub secrets with the new key
