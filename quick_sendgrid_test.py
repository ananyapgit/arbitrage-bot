#!/usr/bin/env python3
"""
Quick test for new SendGrid API key
"""
import os
from sendgrid_notifier import SendGridNotifier

# Test with your new API key
# os.environ["SENDGRID_API_KEY"] = "YOUR_NEW_KEY_HERE"
# os.environ["SENDGRID_FROM_EMAIL"] = "ananyap.workmail@gmail.com"

notifier = SendGridNotifier()
test_deal = {
    "id": "test-123",
    "title": "Test Deal - API Key Verification",
    "price": "₹999",
    "original_price": "₹1999", 
    "affiliate_url": "https://amazon.in/test/dp/B123456789",
    "source": "test",
    "category": "test"
}

print("🧪 Testing SendGrid with new API key...")
try:
    sent = notifier.broadcast_loot_deal(test_deal, 50.0)
    if sent > 0:
        print(f"✅ SUCCESS! Sent {sent} emails")
    else:
        print("❌ FAILED - No emails sent")
except Exception as e:
    print(f"❌ ERROR: {e}")
