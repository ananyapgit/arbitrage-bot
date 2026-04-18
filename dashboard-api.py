#!/usr/bin/env python3
"""
Dashboard API - Serves real bot data for Kinetic Command Center
Provides endpoints for deals, delivery audit, emails, and telegram data
"""

import csv
import json
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Data paths
DATA_DIR = "dashboard/public/data"
MASTER_LOG = os.path.join(DATA_DIR, "master_log.csv")
DELIVERY_AUDIT = os.path.join(DATA_DIR, "delivery_audit.csv")
EMAIL_LOG = os.path.join(DATA_DIR, "email_log.csv")
TELEGRAM_LOG = os.path.join(DATA_DIR, "telegram_log.csv")

def read_csv_data(filepath):
    """Read CSV data and return as list of dictionaries"""
    data = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                data = list(reader)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    return data

def parse_datetime(dt_str):
    """Parse datetime string to datetime object"""
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        return datetime.now()

@app.route('/api/deals')
def get_deals():
    """Get all deals from master_log.csv"""
    deals = read_csv_data(MASTER_LOG)
    
    # Enhance deals with additional computed fields
    for deal in deals:
        # Calculate discount percentage if not present
        if 'discount_percentage' not in deal and 'price' in deal and 'original_price' in deal:
            try:
                price = float(deal['price'].replace('₹', '').replace(',', '').strip())
                original = float(deal['original_price'].replace('₹', '').replace(',', '').strip())
                if original > 0:
                    discount = ((original - price) / original) * 100
                    deal['discount_percentage'] = f"{discount:.1f}"
            except:
                deal['discount_percentage'] = "0.0"
        
        # Ensure decision field exists
        if 'decision' not in deal:
            # Infer decision from affiliate_valid and other fields
            if deal.get('affiliate_valid') == 'true' and deal.get('price') and deal.get('original_price'):
                deal['decision'] = 'accepted'
            else:
                deal['decision'] = 'rejected'
        
        # Ensure reason field exists
        if 'reason' not in deal:
            if deal['decision'] == 'accepted':
                deal['reason'] = 'Valid deal with affiliate link'
            else:
                deal['reason'] = 'Missing required fields or invalid affiliate'
    
    return jsonify(deals)

@app.route('/api/delivery')
def get_delivery_audit():
    """Get delivery audit data"""
    delivery_data = read_csv_data(DELIVERY_AUDIT)
    return jsonify(delivery_data)

@app.route('/api/emails')
def get_emails():
    """Get email log data"""
    emails = read_csv_data(EMAIL_LOG)
    
    # Enhance email data
    for email in emails:
        if 'status' not in email:
            email['status'] = 'sent'
        if 'deal_count' not in email:
            email['deal_count'] = 1
    
    return jsonify(emails)

@app.route('/api/telegram')
def get_telegram():
    """Get telegram log data"""
    telegram_data = read_csv_data(TELEGRAM_LOG)
    
    # Enhance telegram data
    for msg in telegram_data:
        if 'status' not in msg:
            msg['status'] = 'sent'
        if 'views' not in msg:
            msg['views'] = 0
        if 'clicks' not in msg:
            msg['clicks'] = 0
    
    return jsonify(telegram_data)

@app.route('/api/metrics')
def get_metrics():
    """Get comprehensive metrics"""
    deals = read_csv_data(MASTER_LOG)
    delivery_data = read_csv_data(DELIVERY_AUDIT)
    emails = read_csv_data(EMAIL_LOG)
    telegram_data = read_csv_data(TELEGRAM_LOG)
    
    # Calculate metrics
    total_scraped = len(deals)
    total_posted = len([d for d in deals if d.get('decision') == 'accepted'])
    total_rejected = len([d for d in deals if d.get('decision') == 'rejected'])
    efficiency_score = (total_posted / total_scraped * 100) if total_scraped > 0 else 0
    
    # Calculate scraping velocity (deals per minute)
    if deals:
        latest_time = parse_datetime(deals[-1].get('timestamp', ''))
        oldest_time = parse_datetime(deals[0].get('timestamp', ''))
        time_diff = (latest_time - oldest_time).total_seconds() / 60  # minutes
        scraping_velocity = total_scraped / time_diff if time_diff > 0 else 0
    else:
        scraping_velocity = 0
    
    # Broadcast success rate
    successful_broadcasts = len([d for d in delivery_data if d.get('status') == 'success'])
    total_broadcasts = len(delivery_data)
    broadcast_success = (successful_broadcasts / total_broadcasts * 100) if total_broadcasts > 0 else 0
    
    # Daily deals (last 24 hours)
    now = datetime.now()
    yesterday = now - timedelta(hours=24)
    daily_deals = len([d for d in deals if parse_datetime(d.get('timestamp', '')) > yesterday])
    
    # Category statistics
    category_stats = {}
    for deal in deals:
        category = deal.get('category', 'general')
        if category not in category_stats:
            category_stats[category] = {'total': 0, 'accepted': 0, 'rejected': 0}
        category_stats[category]['total'] += 1
        if deal.get('decision') == 'accepted':
            category_stats[category]['accepted'] += 1
        else:
            category_stats[category]['rejected'] += 1
    
    # Source statistics
    source_stats = {}
    for deal in deals:
        source = deal.get('platform', deal.get('source', 'Unknown'))
        if source not in source_stats:
            source_stats[source] = {'total': 0, 'accepted': 0, 'rejected': 0}
        source_stats[source]['total'] += 1
        if deal.get('decision') == 'accepted':
            source_stats[source]['accepted'] += 1
        else:
            source_stats[source]['rejected'] += 1
    
    # Calculate efficiency per source
    for source in source_stats:
        stats = source_stats[source]
        stats['efficiency'] = (stats['accepted'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    metrics = {
        'total_scraped': total_scraped,
        'total_posted': total_posted,
        'total_rejected': total_rejected,
        'efficiency_score': efficiency_score,
        'scraping_velocity': scraping_velocity,
        'broadcast_success': broadcast_success,
        'emails_sent': len([e for e in emails if e.get('status') == 'sent']),
        'telegram_messages': len([t for t in telegram_data if t.get('status') == 'sent']),
        'uptime': 99.7,  # Mock uptime
        'daily_deals': daily_deals,
        'category_stats': category_stats,
        'source_stats': source_stats,
        'last_updated': datetime.now().isoformat()
    }
    
    return jsonify(metrics)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'data_sources': {
            'master_log': os.path.exists(MASTER_LOG),
            'delivery_audit': os.path.exists(DELIVERY_AUDIT),
            'email_log': os.path.exists(EMAIL_LOG),
            'telegram_log': os.path.exists(TELEGRAM_LOG)
        }
    })

# Serve static files
@app.route('/')
def serve_dashboard():
    """Serve the dashboard"""
    return send_from_directory('dashboard-ui/dist', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('dashboard-ui/dist', path)

if __name__ == '__main__':
    print("🚀 Starting Dashboard API Server...")
    print("📊 Available endpoints:")
    print("   GET /api/deals - Get all deals")
    print("   GET /api/delivery - Get delivery audit")
    print("   GET /api/emails - Get email log")
    print("   GET /api/telegram - Get telegram log")
    print("   GET /api/metrics - Get comprehensive metrics")
    print("   GET /api/health - Health check")
    print(f"🌐 Server running on http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
