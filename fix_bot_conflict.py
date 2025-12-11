"""
Quick script to clear Telegram webhook and stop conflicts
Run this before starting app.py if you see conflict errors
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    print("[ERROR] TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

print(f"[INFO] Clearing webhook for bot...")

try:
    # Delete webhook
    delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
    response = requests.get(delete_url, params={"drop_pending_updates": True}, timeout=10)
    
    if response.status_code == 200:
        print("[OK] Webhook deleted successfully!")
        print("[OK] Bot is ready to use polling mode")
    else:
        print(f"[WARNING] Unexpected response: {response.status_code}")
        print(response.text)
        
    # Get bot info to verify
    get_me_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    me_response = requests.get(get_me_url, timeout=10)
    
    if me_response.status_code == 200:
        bot_info = me_response.json()
        if bot_info.get('ok'):
            bot_data = bot_info.get('result', {})
            print(f"[OK] Bot verified: @{bot_data.get('username')}")
            print(f"[OK] Bot name: {bot_data.get('first_name')}")
            
except Exception as e:
    print(f"[ERROR] Failed to clear webhook: {e}")
    print("[INFO] You may need to manually delete webhook or wait a few minutes")

print("\n[INFO] Now you can run: python app.py")

