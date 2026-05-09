#!/usr/bin/env python3
"""
Check SendGrid sender verification status
"""
import os
from sendgrid import SendGridAPIClient

# Use environment variable
if not os.getenv("SENDGRID_API_KEY"):
    print("❌ ERROR: SENDGRID_API_KEY environment variable is not set")
    exit(1)

print("🔍 Checking SendGrid Sender Status")
print("=" * 50)

try:
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    
    # Check verified senders
    response = sg.client.senders.get()
    print(f"📋 Senders API Status: {response.status_code}")
    
    if response.status_code == 200:
        import json
        senders = json.loads(response.body)
        print(f"📧 Found {len(senders)} verified senders:")
        
        for sender in senders:
            print(f"  - {sender.get('from_email', 'N/A')}")
            print(f"    Status: {sender.get('status', 'N/A')}")
            print(f"    Verified: {sender.get('verified', 'N/A')}")
            print()
    
    # Check our specific sender
    print("🔍 Checking ananyap.workmail@gmail.com...")
    
    # Try to get sender info
    try:
        response = sg.client.senders._(os.getenv("SENDGRID_FROM_EMAIL")).get()
        print(f"✅ Sender found: {response.status_code}")
        print(f"Details: {response.body}")
    except Exception as e:
        print(f"❌ Sender not found or not verified: {e}")
    
    # Check domain authentication
    print("\n🌐 Checking domain authentication...")
    try:
        response = sg.client.whitelabel.domains.get()
        print(f"📋 Domain Auth Status: {response.status_code}")
        
        if response.status_code == 200:
            import json
            domains = json.loads(response.body)
            print(f"🌐 Found {len(domains)} authenticated domains:")
            for domain in domains:
                print(f"  - {domain.get('domain', 'N/A')}")
                print(f"    Status: {domain.get('valid', 'N/A')}")
                print(f"    Default: {domain.get('default', 'N/A')}")
    except Exception as e:
        print(f"❌ Domain auth check failed: {e}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n🔧 SOLUTION:")
print("If ananyap.workmail@gmail.com is not verified:")
print("1. Go to: https://app.sendgrid.com/settings/sender_auth")
print("2. Click 'Verify a Single Sender'")
print("3. Enter ananyap.workmail@gmail.com")
print("4. Complete verification process")
print("5. Wait for verification email and click the link")
