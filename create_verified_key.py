#!/usr/bin/env python3
"""
Create a new API key AFTER sender verification
"""

print("🔧 CREATE API KEY AFTER VERIFICATION")
print("=" * 50)

print("""
🚨 IMPORTANT: Create NEW API Key NOW that sender is verified

The sender verification might need time to propagate, but let's try 
creating a NEW API key now that ananyap.workmail@gmail.com is verified.

STEP 1: Create BRAND NEW API Key
1. Go to: https://app.sendgrid.com/settings/api_keys
2. Click "Create API Key"
3. Name: "Arbitrage Bot Verified Sender"
4. API Key Permission: ✅ "Full Access"
5. Click "Create & View"
6. COPY THE NEW KEY IMMEDIATELY

STEP 2: Test the New Key
Once you have the new key, I'll test it immediately.

STEP 3: Update GitHub Secrets
If the test succeeds:
1. Go to repository → Settings → Secrets and variables → Actions
2. Update SENDGRID_API_KEY with the working key
3. GitHub workflow will work immediately

WHY THIS MIGHT WORK:
- Sometimes SendGrid needs sender verification BEFORE API key creation
- The verification might take a few minutes to propagate
- A fresh key created after verification often works immediately

The previous key (SG.REDACTED)
was created before the sender was fully verified.

Let's create a new key now that the sender is verified!
""")
