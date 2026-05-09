#!/usr/bin/env python3
"""
Test SendGrid sender verification directly
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Use environment variables
if not os.getenv("SENDGRID_API_KEY"):
    print("❌ ERROR: SENDGRID_API_KEY environment variable is not set")
    exit(1)
os.environ["SENDGRID_FROM_EMAIL"] = os.getenv("SENDGRID_FROM_EMAIL", "ananyap.workmail@gmail.com")

print("🔍 Testing SendGrid Sender Verification")
print("=" * 50)

try:
    # Test 1: Create client
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    print("✅ SendGrid client created successfully")
    
    # Test 2: Test API access
    response = sg.client.api_keys.get()
    print(f"✅ API Access: Status {response.status_code}")
    
    # Test 3: Try to send a simple test email
    message = Mail(
        from_email=os.getenv("SENDGRID_FROM_EMAIL"),
        to_emails='test@example.com',
        subject='SendGrid Test',
        html_content='<strong>This is a test email</strong>'
    )
    
    print("📧 Attempting to send test email...")
    response = sg.send(message)
    print(f"📊 Send Status: {response.status_code}")
    
    if response.status_code == 202:
        print("✅ SUCCESS! Email send accepted")
    elif response.status_code == 401:
        print("❌ 401 Unauthorized - API Key issue")
    elif response.status_code == 403:
        print("❌ 403 Forbidden - Sender verification issue")
    else:
        print(f"⚠️  Unexpected status: {response.status_code}")
        print(f"Response: {response.body}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    
print("\n🔧 If still failing, check:")
print("1. Sender email verification at: https://app.sendgrid.com/settings/sender_auth")
print("2. Domain authentication (DNS records)")
print("3. API Key permissions (must be Full Access)")
