#!/usr/bin/env python3
"""
Mailgun Setup Guide - Step by Step Instructions
"""

print("🔧 MAILGUN SETUP GUIDE")
print("=" * 50)

print("""
🚀 STEP 1: CREATE MAILGUN ACCOUNT
==================================

1. Go to: https://www.mailgun.com/
2. Click "Sign Up" (top right)
3. Choose "Free" plan
4. Fill in:
   - Email: your-email@example.com
   - Password: create strong password
   - Full Name: Your Name
   - Company: ArbiDeals (optional)
5. Click "Create Account"
6. Check your email for verification link
7. Click the verification link

⏰ Time: 2-3 minutes

🎯 STEP 2: GET YOUR CREDENTIALS
===============================

1. After verification, you'll be in Mailgun dashboard
2. Look for "Domains" in the left menu
3. You'll see a "Sandbox Domain" like: sandbox1234567890.mailgun.org
4. Click on the sandbox domain
5. You'll see:
   - API Key: key-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   - Domain: sandbox1234567890.mailgun.org
   - SMTP Login: postmaster@sandbox1234567890.mailgun.org

📝 COPY THESE THREE VALUES:
1. API Key (starts with "key-")
2. Domain (sandbox domain)
3. Your verified email address

⏰ Time: 1 minute

🔧 STEP 3: UPDATE GITHUB SECRETS
=================================

1. Go to your GitHub repository
2. Click "Settings" → "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add these secrets:

   MAILGUN_API_KEY: key-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   MAILGUN_DOMAIN: sandbox1234567890.mailgun.org
   MAILGUN_FROM_EMAIL: your-verified-email@example.com

⏰ Time: 2 minutes

🧪 STEP 4: TEST INTEGRATION
===========================

Once you have the credentials, I'll:
1. Test the Mailgun integration locally
2. Update the main bot code
3. Test in GitHub workflow
4. Confirm emails are working

🎯 EXPECTED RESULTS:
- 5,000 free emails per month
- Reliable delivery
- No account restrictions
- Working GitHub workflow

🚀 READY TO START?
==================

Please:
1. Create the Mailgun account
2. Get the API key and domain
3. Share them with me
4. I'll handle the rest!

The setup is very quick and you'll have working emails immediately!
""")

print("\n📋 QUICK CHECKLIST:")
print("□ Create Mailgun account")
print("□ Verify email")
print("□ Get API key from dashboard")
print("□ Get sandbox domain")
print("□ Add secrets to GitHub")
print("□ Test with me")

print("\n🎯 Once you have the credentials, just share them and I'll set everything up!")
