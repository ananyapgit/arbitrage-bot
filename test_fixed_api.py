#!/usr/bin/env python3
"""
Test after fixing API key permissions
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def test_fixed_permissions():
    """Test with fixed API key permissions"""
    
    # Set your new API key here
    api_key = os.getenv("SENDGRID_API_KEY", "YOUR_NEW_API_KEY_HERE")
    from_email = "ananyap.workmail@gmail.com"
    
    print("🧪 Testing Fixed API Key")
    print("=" * 30)
    
    try:
        client = SendGridAPIClient(api_key)
        
        # Test mail send specifically
        message = Mail(
            from_email=from_email,
            to_emails="ananyakumarleo@gmail.com",
            subject='✅ SendGrid Fixed - Test Email',
            html_content='''
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>🎉 SendGrid API Key Fixed!</h2>
                <p>Your arbitrage bot email system is now working.</p>
                <p>This test confirms the API key has mail send permissions.</p>
                <hr>
                <p><small>From: Arbitrage Bot System</small></p>
            </div>
            '''
        )
        
        resp = client.send(message)
        print(f"✅ SUCCESS! Status: {resp.status_code}")
        
        if resp.status_code == 202:
            print("🎉 Email sent successfully!")
            print("Your GitHub workflow will now work!")
        else:
            print(f"⚠️  Unexpected status: {resp.status_code}")
            
    except Exception as e:
        print(f"❌ Still failing: {e}")
        
        if "401" in str(e):
            print("🚨 Still 401 - API key still lacks mail send permissions")
        elif "403" in str(e):
            print("🚨 403 - Sender email not verified")

if __name__ == "__main__":
    test_fixed_permissions()
