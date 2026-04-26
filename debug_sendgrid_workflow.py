#!/usr/bin/env python3
"""
Debug SendGrid exactly like the GitHub workflow does
"""
import os
import sys
from sendgrid_notifier import SendGridNotifier

def test_workflow_sendgrid():
    """Test SendGrid exactly like the workflow does"""
    
    print("🔍 Debugging SendGrid in workflow context...")
    print("=" * 50)
    
    # Check environment variables (like GitHub workflow)
    print("📋 Environment Variables:")
    sendgrid_key = os.getenv("SENDGRID_API_KEY", "")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "")
    
    print(f"SENDGRID_API_KEY exists: {bool(sendgrid_key)}")
    print(f"SENDGRID_API_KEY length: {len(sendgrid_key)}")
    print(f"SENDGRID_API_KEY starts with: {sendgrid_key[:6] if sendgrid_key else 'None'}")
    print(f"SENDGRID_FROM_EMAIL: {from_email}")
    
    # Test SendGridNotifier initialization (exactly like bot.py)
    print("\n🧪 Testing SendGridNotifier initialization...")
    try:
        notifier = SendGridNotifier()
        print(f"✅ SendGridNotifier initialized")
        print(f"📧 API Key loaded: {bool(notifier.api_key)}")
        print(f"📧 From Email: {notifier.from_email}")
        
        # Test subscriber loading
        print("\n📋 Testing subscriber loading...")
        subscribers = notifier.load_subscribers()
        print(f"👥 Subscribers loaded: {len(subscribers)}")
        if subscribers:
            print(f"📧 First subscriber: {subscribers[0]}")
        
        # Test actual email send (like in workflow)
        if subscribers and notifier.api_key and notifier.from_email:
            print("\n🚀 Testing actual email send...")
            test_deal = {
                "id": "test-deal-123",
                "title": "Test Deal - SendGrid Debug",
                "price": "₹999",
                "original_price": "₹1999", 
                "affiliate_url": "https://example.com/test",
                "source": "debug",
                "category": "test"
            }
            
            try:
                sent = notifier.broadcast_loot_deal(test_deal, 50.0)  # 50% discount
                print(f"📊 Email send result: {sent}")
                return sent > 0
            except Exception as e:
                print(f"❌ Email send failed: {e}")
                return False
        else:
            print("⚠️  Missing prerequisites for email test")
            return False
            
    except Exception as e:
        print(f"❌ SendGridNotifier failed: {e}")
        return False

if __name__ == "__main__":
    # Simulate GitHub workflow environment
    print("🔧 Setting up test environment...")
    
    # You can set these manually to test:
    # os.environ["SENDGRID_API_KEY"] = "your_new_key_here"
    # os.environ["SENDGRID_FROM_EMAIL"] = "your_verified_sender@example.com"
    
    success = test_workflow_sendgrid()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ WORKFLOW TEST PASSED")
        print("Your GitHub workflow should work with the current setup")
    else:
        print("❌ WORKFLOW TEST FAILED")
        print("Issues found that need to be fixed before workflow will work")
    
    print("\n🔧 To fix:")
    print("1. Generate new SendGrid API key")
    print("2. Update SENDGRID_API_KEY in GitHub secrets")
    print("3. Verify SENDGRID_FROM_EMAIL is a verified sender")
    print("4. Ensure subscribers.txt has valid emails")
