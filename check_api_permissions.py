#!/usr/bin/env python3
"""
Check exact API key permissions
"""
import os
import json
from sendgrid import SendGridAPIClient

# Use environment variable
if not os.getenv("SENDGRID_API_KEY"):
    print("❌ ERROR: SENDGRID_API_KEY environment variable is not set")
    exit(1)

print("🔍 CHECKING API KEY PERMISSIONS")
print("=" * 50)

try:
    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    
    # Get all API keys
    response = sg.client.api_keys.get()
    print(f"📋 API Keys Status: {response.status_code}")
    
    if response.status_code == 200:
        keys_data = json.loads(response.body)
        print(f"🔑 Found {len(keys_data)} API keys")
        
        for key in keys_data:
            print(f"\n🔑 Key Details:")
            print(f"  Name: {key['name'] if 'name' in key else 'N/A'}")
            print(f"  API Key ID: {key['api_key_id'] if 'api_key_id' in key else 'N/A'}")
            print(f"  Created At: {key['created_at'] if 'created_at' in key else 'N/A'}")
            print(f"  Updated At: {key['updated_at'] if 'updated_at' in key else 'N/A'}")
            
            # Check permissions
            permissions = key['permissions'] if 'permissions' in key else []
            print(f"  Permissions: {len(permissions)} permissions")
            
            for perm in permissions:
                print(f"    - {perm}")
            
            # Check if it has mail send permission
            has_mail_send = any('mail' in str(perm).lower() and 'send' in str(perm).lower() for perm in permissions)
            print(f"  Has Mail Send: {has_mail_send}")
            
            # Check if it's full access
            is_full_access = any('full' in str(perm).lower() for perm in permissions)
            print(f"  Is Full Access: {is_full_access}")
    
    print("\n🔧 SOLUTION:")
    print("If the API key doesn't have 'mail.send' permission:")
    print("1. Go to: https://app.sendgrid.com/settings/api_keys")
    print("2. Find the key 'Arbitrage Bot Verified Sender'")
    print("3. Click 'Edit' or delete and recreate")
    print("4. Ensure 'Mail Send' permission is checked")
    print("5. Or select 'Full Access' to be safe")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n🚨 LIKELY ISSUE:")
print("The API key was created with limited permissions instead of 'Full Access'")
print("Even though 'Full Access' was selected, it might not have been applied correctly")
