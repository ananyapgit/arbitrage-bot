#!/usr/bin/env python3
"""
Deep SendGrid debugging - check account level issues
"""
import os
import json
from sendgrid import SendGridAPIClient

# Use environment variable
if not os.getenv("SENDGRID_API_KEY"):
    print("❌ ERROR: SENDGRID_API_KEY environment variable is not set")
    exit(1)

print("🔍 DEEP SENDGRID DEBUG")
print("=" * 50)

try:
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    
    # Test 1: Check account info
    print("📋 Checking account info...")
    try:
        response = sg.client.user.account.get()
        print(f"✅ Account access: {response.status_code}")
        if response.status_code == 200:
            account_data = json.loads(response.body)
            print(f"📧 Account email: {account_data.get('email', 'N/A')}")
            print(f"📊 Account type: {account_data.get('type', 'N/A')}")
            print(f"📈 Reputation: {account_data.get('reputation', 'N/A')}")
    except Exception as e:
        print(f"❌ Account check failed: {e}")
    
    # Test 2: Check API key details
    print("\n🔑 Checking API key permissions...")
    try:
        response = sg.client.api_keys.get()
        print(f"✅ API Keys access: {response.status_code}")
        if response.status_code == 200:
            keys_data = json.loads(response.body)
            print(f"🔑 Found {len(keys_data)} API keys")
            
            # Find our key
            for key in keys_data:
                if key.get('api_key_id'):
                    print(f"  - Key ID: {key.get('api_key_id', 'N/A')}")
                    print(f"    Name: {key.get('name', 'N/A')}")
                    print(f"    Permissions: {key.get('permissions', 'N/A')}")
                    print()
    except Exception as e:
        print(f"❌ API key check failed: {e}")
    
    # Test 3: Check email activity limits
    print("\n📊 Checking email limits...")
    try:
        response = sg.client.user.email.get()
        print(f"✅ Email limits access: {response.status_code}")
        if response.status_code == 200:
            limits_data = json.loads(response.body)
            print(f"📧 Daily limit: {limits_data.get('daily_limit', 'N/A')}")
            print(f"📧 Remaining: {limits_data.get('remaining', 'N/A')}")
            print(f"📧 Reset date: {limits_data.get('reset_date', 'N/A')}")
    except Exception as e:
        print(f"❌ Email limits check failed: {e}")
    
    # Test 4: Try different API endpoint
    print("\n🧪 Testing mail send endpoint directly...")
    try:
        from sendgrid.helpers.mail import Mail
        
        # Create a simple test email
        message = Mail(
            from_email=os.getenv("SENDGRID_FROM_EMAIL"),
            to_emails='test@example.com',
            subject='Direct API Test',
            html_content='<strong>Test email</strong>'
        )
        
        # Try to send
        response = sg.send(message)
        print(f"📊 Direct send status: {response.status_code}")
        
        if response.status_code == 202:
            print("✅ SUCCESS! Email accepted by SendGrid")
        elif response.status_code == 401:
            print("❌ 401 - Authentication failed")
            print(f"Response body: {response.body}")
        elif response.status_code == 403:
            print("❌ 403 - Forbidden (likely sender/permission issue)")
            print(f"Response body: {response.body}")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            print(f"Response body: {response.body}")
            
    except Exception as e:
        print(f"❌ Direct send failed: {e}")
    
    # Test 5: Check if we can access mail settings
    print("\n⚙️ Checking mail settings access...")
    try:
        response = sg.client.mail.settings.get()
        print(f"✅ Mail settings access: {response.status_code}")
        if response.status_code == 200:
            settings_data = json.loads(response.body)
            print(f"⚙️ Settings available: {len(settings_data)}")
    except Exception as e:
        print(f"❌ Mail settings check failed: {e}")

except Exception as e:
    print(f"❌ General error: {e}")

print("\n🔧 POSSIBLE ISSUES:")
print("1. API key doesn't have 'Mail Send' permission")
print("2. Account is suspended or restricted")
print("3. Daily email limit reached")
print("4. Sender verification still propagating")
print("5. IP address blocked by SendGrid")
