#!/usr/bin/env python3
"""
Debug script to check GitHub secrets injection
"""
import os

def debug_secrets():
    """Check if secrets are being passed correctly"""
    
    print("🔍 GitHub Secrets Debug Check")
    print("=" * 40)
    
    # Check SENDGRID_API_KEY
    key = os.getenv('SENDGRID_API_KEY')
    print(f"DEBUG: SENDGRID_API_KEY length is {len(key) if key else 0}")
    print(f"DEBUG: SENDGRID_API_KEY starts with {key[:6] if key else 'None'}")
    
    # Check SENDGRID_FROM_EMAIL
    from_email = os.getenv('SENDGRID_FROM_EMAIL')
    print(f"DEBUG: SENDGRID_FROM_EMAIL is {from_email}")
    
    # Check other secrets for comparison
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    print(f"DEBUG: TELEGRAM_BOT_TOKEN length is {len(telegram_token) if telegram_token else 0}")
    print(f"DEBUG: TELEGRAM_BOT_TOKEN starts with {telegram_token[:10] if telegram_token else 'None'}")
    
    chat_id = os.getenv('CHAT_ID')
    print(f"DEBUG: CHAT_ID is {chat_id}")
    
    # Summary
    print("\n📋 Secrets Status:")
    print(f"✅ SENDGRID_API_KEY: {'Loaded' if key and len(key) > 0 else 'MISSING'}")
    print(f"✅ SENDGRID_FROM_EMAIL: {'Loaded' if from_email else 'MISSING'}")
    print(f"✅ TELEGRAM_BOT_TOKEN: {'Loaded' if telegram_token and len(telegram_token) > 0 else 'MISSING'}")
    print(f"✅ CHAT_ID: {'Loaded' if chat_id else 'MISSING'}")
    
    # Test if we can import SendGrid (for environment check)
    print("\n🧪 Environment Check:")
    try:
        from sendgrid import SendGridAPIClient
        print("✅ SendGrid library available")
        
        if key and len(key) > 0:
            try:
                client = SendGridAPIClient(key)
                print("✅ SendGrid client created")
            except Exception as e:
                print(f"❌ SendGrid client failed: {e}")
        else:
            print("❌ Cannot create SendGrid client - no API key")
            
    except ImportError:
        print("❌ SendGrid library not available")
    
    return key, from_email

if __name__ == "__main__":
    debug_secrets()
