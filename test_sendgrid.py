#!/usr/bin/env python3
"""
Test SendGrid API Key - Run this locally to verify your API key works
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def test_sendgrid_api():
    """Test SendGrid API key with a simple test email"""
    
    # Get API key from environment or prompt
    api_key = os.getenv("SENDGRID_API_KEY") or input("Enter your SendGrid API key: ").strip()
    from_email = os.getenv("SENDGRID_FROM_EMAIL") or input("Enter your verified sender email: ").strip()
    test_email = input("Enter your test email address: ").strip()
    
    if not api_key or not from_email or not test_email:
        print("❌ Missing required credentials")
        return False
    
    print(f"🔑 Testing SendGrid API key: {api_key[:6]}...")
    print(f"📧 From: {from_email}")
    print(f"📧 To: {test_email}")
    
    try:
        # Create test message
        message = Mail(
            from_email=from_email,
            to_emails=test_email,
            subject='🧪 SendGrid API Test - Arbitrage Bot',
            html_content='''
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>✅ SendGrid API Test Successful!</h2>
                <p>Your SendGrid API key is working correctly.</p>
                <p>The arbitrage bot email system should now work properly.</p>
                <hr>
                <p><small>Test sent from Arbitrage Bot System</small></p>
            </div>
            '''
        )
        
        # Send test email
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        print(f"✅ Email sent successfully!")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 202:
            print("🎉 SendGrid API key is working perfectly!")
            return True
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 SendGrid API Key Test")
    print("=" * 40)
    success = test_sendgrid_api()
    
    if success:
        print("\n✅ TEST PASSED - Update your GitHub secrets with these values:")
        print(f"SENDGRID_API_KEY: {os.getenv('SENDGRID_API_KEY', 'YOUR_API_KEY_HERE')}")
        print(f"SENDGRID_FROM_EMAIL: {os.getenv('SENDGRID_FROM_EMAIL', 'YOUR_EMAIL_HERE')}")
    else:
        print("\n❌ TEST FAILED - Check your API key and sender email")
