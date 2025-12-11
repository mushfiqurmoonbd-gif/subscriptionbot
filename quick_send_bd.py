"""
Quick script to send SMS to Bangladeshi number: +8801701259687
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from sms_sender import send_sms_via_twilio

def main():
    phone_number = "+8801701259687"
    message = "Hello! This is a test message from your subscription service."
    
    print("=" * 70)
    print("QUICK SMS SENDER - BANGLADESH")
    print("=" * 70)
    print(f"\nTo: {phone_number}")
    print(f"Message: {message}")
    print("\n" + "-" * 70)
    
    # Check if Twilio is configured
    if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN:
        print("\n[ERROR] Twilio not configured!")
        print("\nTo send SMS to Bangladeshi numbers, you need Twilio:")
        print("\n1. Sign up: https://www.twilio.com/")
        print("2. Get credentials from Twilio dashboard")
        print("3. Add to .env file:")
        print("   TWILIO_ACCOUNT_SID=your_account_sid")
        print("   TWILIO_AUTH_TOKEN=your_auth_token")
        print("   TWILIO_PHONE_NUMBER=+1234567890")
        print("\n4. Install Twilio: pip install twilio")
        print("\n" + "=" * 70)
        return
    
    # Send SMS
    print("\n[INFO] Sending SMS...")
    success = send_sms_via_twilio(phone_number, message)
    
    print("\n" + "=" * 70)
    if success:
        print("[SUCCESS] Message sent!")
    else:
        print("[ERROR] Failed to send message")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

