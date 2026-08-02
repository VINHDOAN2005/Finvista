# -*- coding: utf-8 -*-
"""
Setup script for Telegram Webhook
This script sets up the webhook URL for your Telegram bot.
"""

import os
import sys
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infra.telegram_alerts import load_telegram_config

def setup_webhook(webhook_url: str):
    """Set up the webhook for Telegram bot"""
    config = load_telegram_config()
    token = config.get("telegram_bot_token", "").strip()
    
    if not token or "YOUR_TELEGRAM" in token:
        print("❌ Telegram bot token not configured!")
        print("💡 Please set TELEGRAM_BOT_TOKEN in .env file or telegram_config.json")
        return False
    
    # Set webhook
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = {
        "url": webhook_url
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get('ok'):
                print(f"✅ Webhook set successfully!")
                print(f"📡 Webhook URL: {webhook_url}")
                return True
            else:
                print(f"❌ Failed to set webhook: {result.get('description')}")
                return False
        else:
            print(f"❌ Error setting webhook: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def delete_webhook():
    """Delete the webhook (switch back to polling)"""
    config = load_telegram_config()
    token = config.get("telegram_bot_token", "").strip()
    
    if not token or "YOUR_TELEGRAM" in token:
        print("❌ Telegram bot token not configured!")
        return False
    
    url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    
    try:
        resp = requests.post(url, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get('ok'):
                print(f"✅ Webhook deleted successfully!")
                return True
            else:
                print(f"❌ Failed to delete webhook: {result.get('description')}")
                return False
        else:
            print(f"❌ Error: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_webhook_info():
    """Get current webhook information"""
    config = load_telegram_config()
    token = config.get("telegram_bot_token", "").strip()
    
    if not token or "YOUR_TELEGRAM" in token:
        print("❌ Telegram bot token not configured!")
        return False
    
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get('ok'):
                info = result.get('result', {})
                print("📊 Current Webhook Info:")
                print(f"  URL: {info.get('url', 'Not set')}")
                print(f"  Has custom certificate: {info.get('has_custom_certificate', False)}")
                print(f"  Pending update count: {info.get('pending_update_count', 0)}")
                print(f"  Last error date: {info.get('last_error_date', 'None')}")
                print(f"  Last error message: {info.get('last_error_message', 'None')}")
                return True
            else:
                print(f"❌ Failed to get webhook info: {result.get('description')}")
                return False
        else:
            print(f"❌ Error: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Telegram Webhook")
    parser.add_argument('--set', help='Set webhook URL')
    parser.add_argument('--delete', action='store_true', help='Delete webhook')
    parser.add_argument('--info', action='store_true', help='Get webhook info')
    
    args = parser.parse_args()
    
    if args.set:
        setup_webhook(args.set)
    elif args.delete:
        delete_webhook()
    elif args.info:
        get_webhook_info()
    else:
        print("Usage:")
        print("  python setup_telegram_webhook.py --set <WEBHOOK_URL>")
        print("  python setup_telegram_webhook.py --delete")
        print("  python setup_telegram_webhook.py --info")
        print("\nExample:")
        print("  python setup_telegram_webhook.py --set https://your-domain.com/webhook/telegram")
