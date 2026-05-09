#!/usr/bin/env python3
"""
Mailgun Email Notifier - Backup to SendGrid
"""
import os
import requests
from typing import List, Dict, Any

class MailgunNotifier:
    def __init__(self) -> None:
        self.api_key = (os.getenv("MAILGUN_API_KEY") or "").strip()
        self.domain = (os.getenv("MAILGUN_DOMAIN") or "").strip()
        self.from_email = (os.getenv("MAILGUN_FROM_EMAIL") or "").strip()
        
        if self.api_key and self.domain and self.from_email:
            print(f"[DEBUG] Mailgun initialized for domain: {self.domain}", flush=True)
        else:
            print("[DEBUG] Mailgun not configured - missing credentials", flush=True)
    
    def load_subscribers(self) -> List[str]:
        """Load email subscribers from file"""
        try:
            with open('dashboard/public/data/subscribers.txt', 'r') as f:
                subscribers = [line.strip() for line in f if line.strip() and '@' in line]
            print(f"[DEBUG] Loaded {len(subscribers)} subscribers for Mailgun", flush=True)
            return subscribers
        except FileNotFoundError:
            print("[DEBUG] No subscribers file found for Mailgun", flush=True)
            return []
    
    def send_email(self, to_emails: List[str], subject: str, html_content: str) -> int:
        """Send email via Mailgun"""
        if not self.api_key or not self.domain or not self.from_email:
            print("[ERROR] Mailgun credentials not configured", flush=True)
            return 0
        
        sent_count = 0
        for email in to_emails:
            try:
                response = requests.post(
                    f"https://api.mailgun.net/v3/{self.domain}/messages",
                    auth=("api", self.api_key),
                    data={
                        "from": f"ArbiDeals <{self.from_email}>",
                        "to": email,
                        "subject": subject,
                        "html": html_content
                    }
                )
                
                if response.status_code == 200:
                    sent_count += 1
                    print(f"[MAILGUN] Sent to {email}", flush=True)
                else:
                    print(f"[MAILGUN] Failed to send to {email}: {response.status_code}", flush=True)
                    
            except Exception as e:
                print(f"[MAILGUN] Error sending to {email}: {e}", flush=True)
        
        return sent_count
    
    def broadcast_loot_deal(self, deal: Dict[str, Any], discount_percentage: float) -> int:
        """Send loot deal email via Mailgun"""
        subscribers = self.load_subscribers()
        if not subscribers:
            return 0
        
        # Create HTML email
        title = deal.get('title', 'Unknown Deal')
        price = deal.get('price', 'Check Price')
        original_price = deal.get('original_price', '')
        affiliate_url = deal.get('affiliate_url', '')
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ff6b35;">🔥 {discount_percentage:.0f}% OFF - {title}</h2>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #28a745; margin: 0;">💰 Price: {price}</h3>
                {f'<p style="color: #6c757d; text-decoration: line-through; margin: 5px 0;">Original: {original_price}</p>' if original_price else ''}
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{affiliate_url}" 
                   style="background: #ff6b35; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 5px; font-weight: bold;">
                    🛍️ Buy Now
                </a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #6c757d; font-size: 12px;">
                You're receiving this because you subscribed to ArbiDeals.<br>
                <a href="#">Unsubscribe</a> | <a href="#">View more deals</a>
            </p>
        </body>
        </html>
        """
        
        subject = f"🔥 {discount_percentage:.0f}% OFF - {title}"
        return self.send_email(subscribers, subject, html_content)

# Test function
def test_mailgun():
    """Test Mailgun configuration"""
    print("🧪 Testing Mailgun...")
    
    # Set test credentials (you'll need to update these)
    os.environ["MAILGUN_API_KEY"] = "your-mailgun-api-key"
    os.environ["MAILGUN_DOMAIN"] = "your-domain.mailgun.org"
    os.environ["MAILGUN_FROM_EMAIL"] = "your-email@your-domain.com"
    
    notifier = MailgunNotifier()
    
    test_deal = {
        "title": "Test Deal - Mailgun",
        "price": "₹999",
        "original_price": "₹1999",
        "affiliate_url": "https://example.com/test"
    }
    
    sent = notifier.broadcast_loot_deal(test_deal, 50.0)
    print(f"📊 Mailgun test result: {sent} emails sent")

if __name__ == "__main__":
    test_mailgun()
