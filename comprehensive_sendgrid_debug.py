#!/usr/bin/env python3
"""
Comprehensive SendGrid debugging - all possible angles
"""
import os
import json
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Use environment variable
if not os.getenv("SENDGRID_API_KEY"):
    print("❌ ERROR: SENDGRID_API_KEY environment variable is not set")
    exit(1)
os.environ["SENDGRID_FROM_EMAIL"] = os.getenv("SENDGRID_FROM_EMAIL", "ananyap.workmail@gmail.com")

print("🔍 COMPREHENSIVE SENDGRID DEBUG")
print("=" * 60)

# Test 1: Direct HTTP request to SendGrid API
print("🌐 TEST 1: Direct HTTP Request")
try:
    headers = {
        'Authorization': f'Bearer {os.getenv("SENDGRID_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    # Test basic API access
    response = requests.get('https://api.sendgrid.com/v3/user/account', headers=headers)
    print(f"📋 Direct API Access: {response.status_code}")
    
    if response.status_code == 200:
        account_data = response.json()
        print(f"📧 Account: {account_data.get('email', 'N/A')}")
        print(f"📊 Type: {account_data.get('type', 'N/A')}")
        print(f"📈 Reputation: {account_data.get('reputation', 'N/A')}")
    
except Exception as e:
    print(f"❌ Direct HTTP failed: {e}")

# Test 2: SendGrid library with different approach
print("\n📧 TEST 2: SendGrid Library Debug")
try:
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    
    # Test API key validation
    print("🔑 Testing API key validation...")
    response = sg.client.api_keys._(os.getenv("SENDGRID_API_KEY").split('.')[0]).get()
    print(f"🔑 Key validation: {response.status_code}")
    
except Exception as e:
    print(f"❌ Library test failed: {e}")

# Test 3: Check sender verification status via API
print("\n✅ TEST 3: Sender Verification Status")
try:
    headers = {
        'Authorization': f'Bearer {os.getenv("SENDGRID_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    # Get all verified senders
    response = requests.get('https://api.sendgrid.com/v3/senders', headers=headers)
    print(f"📋 Senders API: {response.status_code}")
    
    if response.status_code == 200:
        senders = response.json()
        print(f"📧 Found {len(senders)} senders")
        
        our_sender_found = False
        for sender in senders:
            sender_email = sender.get('from_email', '')
            if sender_email == 'ananyap.workmail@gmail.com':
                our_sender_found = True
                print(f"✅ Our sender found!")
                print(f"   Status: {sender.get('status', 'N/A')}")
                print(f"   Verified: {sender.get('verified', 'N/A')}")
                print(f"   Verification: {sender.get('verification', {})}")
                break
        
        if not our_sender_found:
            print("❌ Our sender not found in API response")
            print("📋 Available senders:")
            for sender in senders:
                print(f"   - {sender.get('from_email', 'N/A')}")
    
except Exception as e:
    print(f"❌ Sender check failed: {e}")

# Test 4: Try sending with minimal payload
print("\n📬 TEST 4: Minimal Email Payload")
try:
    headers = {
        'Authorization': f'Bearer {os.getenv("SENDGRID_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    # Minimal email payload
    email_data = {
        "personalizations": [
            {
                "to": [{"email": "test@example.com"}],
                "subject": "Test Email"
            }
        ],
        "from": {"email": "ananyap.workmail@gmail.com"},
        "content": [
            {"type": "text/plain", "value": "Test email content"}
        ]
    }
    
    response = requests.post('https://api.sendgrid.com/v3/mail/send', 
                           headers=headers, 
                           json=email_data)
    
    print(f"📬 Minimal send status: {response.status_code}")
    print(f"📬 Response headers: {dict(response.headers)}")
    
    if response.status_code == 202:
        print("✅ SUCCESS! Minimal email accepted")
    elif response.status_code == 401:
        print("❌ 401 - Authentication failed")
        print(f"Response body: {response.text}")
    elif response.status_code == 403:
        print("❌ 403 - Forbidden")
        print(f"Response body: {response.text}")
    else:
        print(f"⚠️  Status: {response.status_code}")
        print(f"Response body: {response.text}")
    
except Exception as e:
    print(f"❌ Minimal send failed: {e}")

# Test 5: Check account restrictions
print("\n🚫 TEST 5: Account Restrictions")
try:
    headers = {
        'Authorization': f'Bearer {os.getenv("SENDGRID_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    # Check suppression list
    response = requests.get('https://api.sendgrid.com/v3/suppression/bounces', headers=headers)
    print(f"🚫 Suppression check: {response.status_code}")
    
    # Check blocks
    response = requests.get('https://api.sendgrid.com/v3/suppression/blocks', headers=headers)
    print(f"🚫 Blocks check: {response.status_code}")
    
    # Check email activity
    response = requests.get('https://api.sendgrid.com/v3/messages', headers=headers)
    print(f"📊 Email activity: {response.status_code}")
    
except Exception as e:
    print(f"❌ Restriction check failed: {e}")

# Test 6: Check IP reputation
print("\n🌍 TEST 6: IP Reputation Check")
try:
    headers = {
        'Authorization': f'Bearer {os.getenv("SENDGRID_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get('https://api.sendgrid.com/v3/ip_warmup', headers=headers)
    print(f"🌍 IP warmup: {response.status_code}")
    
except Exception as e:
    print(f"❌ IP check failed: {e}")

print("\n🔧 POSSIBLE ISSUES BEYOND API KEY:")
print("1. Sender verification not fully propagated (can take 5-10 minutes)")
print("2. Account is in 'sandbox mode' or restricted")
print("3. IP address blocked by SendGrid")
print("4. Domain authentication issues")
print("5. SendGrid account requires additional verification")
print("6. Rate limiting on new accounts")
print("7. Geographic restrictions on the account")

print("\n🎯 NEXT STEPS:")
print("1. Wait 5-10 minutes for sender verification to propagate")
print("2. Check SendGrid dashboard for any account warnings")
print("3. Try sending from SendGrid dashboard directly")
print("4. Check if account needs phone verification")
