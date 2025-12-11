"""
Send SMS to Bangladeshi phone number
This script sends SMS to +8801701259687
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def send_sms_direct(phone_number, message):
    """
    Send SMS directly to Bangladeshi number using SMS API or alternative method.
    
    For Bangladesh, we need an SMS API service like:
    - Twilio (supports Bangladesh)
    - Nexmo/Vonage
    - Or email-to-SMS if carrier supports it
    
    This is a basic implementation - you'll need to configure an SMS API.
    """
    
    # Option 1: Try using Twilio (if configured)
    try:
        from twilio.rest import Client
        from config import Config
        
        # Check if Twilio is configured
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if account_sid and auth_token and twilio_number:
            client = Client(account_sid, auth_token)
            message_obj = client.messages.create(
                body=message,
                from_=twilio_number,
                to=phone_number
            )
            print(f"[OK] SMS sent via Twilio! SID: {message_obj.sid}")
            return True
        else:
            print("[INFO] Twilio not configured. Trying alternative method...")
    except ImportError:
        print("[INFO] Twilio not installed. Install with: pip install twilio")
    except Exception as e:
        print(f"[WARNING] Twilio error: {e}")
    
    # Option 2: Try using email-to-SMS (works for some carriers)
    # Note: Most Bangladeshi carriers don't support this, but we'll try
    try:
        from sms_sender import send_sms_via_email
        from config import Config
        
        # For Bangladesh, we need to know the carrier
        # Common Bangladeshi carriers: Grameenphone, Robi, Banglalink, Teletalk
        # Unfortunately, these don't have email-to-SMS gateways
        
        print("[INFO] Email-to-SMS gateways are not available for Bangladeshi carriers.")
        print("[INFO] You need to use an SMS API service like Twilio.")
        
    except Exception as e:
        print(f"[ERROR] Email-to-SMS error: {e}")
    
    # Option 3: Print instructions
    print("\n" + "=" * 70)
    print("TO SEND SMS TO BANGLADESHI NUMBERS:")
    print("=" * 70)
    print("\n1. Sign up for Twilio: https://www.twilio.com/")
    print("2. Get Account SID, Auth Token, and a phone number")
    print("3. Add to .env file:")
    print("   TWILIO_ACCOUNT_SID=your_account_sid")
    print("   TWILIO_AUTH_TOKEN=your_auth_token")
    print("   TWILIO_PHONE_NUMBER=+1234567890")
    print("\n4. Install Twilio: pip install twilio")
    print("\n5. Run this script again")
    print("\n" + "=" * 70)
    
    return False

def send_via_smtp_test(phone_number, message):
    """
    Alternative: Try sending via SMTP directly (may not work for BD carriers).
    This is just a test - most Bangladeshi carriers don't support email-to-SMS.
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from config import Config
        
        # Format: For some carriers, you might try: number@carrier-domain
        # But this typically doesn't work for Bangladeshi carriers
        
        # Clean phone number (remove + and keep digits)
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        
        # Try common formats (these may not work, but worth trying)
        # Note: These are just examples - actual carriers may not support this
        
        smtp_config = {
            'server': Config.SMTP_SERVER,
            'port': Config.SMTP_PORT,
            'username': Config.SMTP_USERNAME,
            'password': Config.SMTP_PASSWORD,
            'from_email': Config.SMTP_FROM_EMAIL or Config.SMTP_USERNAME
        }
        
        # Try Grameenphone format (if they had email-to-SMS, which they don't)
        # This is just a demonstration - it won't actually work
        print(f"[INFO] Attempting to send via SMTP (may not work for BD carriers)...")
        print(f"[INFO] Phone: {clean_phone}")
        print(f"[INFO] Message: {message}")
        print(f"[WARNING] Most Bangladeshi carriers don't support email-to-SMS.")
        print(f"[WARNING] You need an SMS API service like Twilio.")
        
        return False
        
    except Exception as e:
        print(f"[ERROR] SMTP test failed: {e}")
        return False

def main():
    phone_number = "+8801701259687"
    message = "Hello from Subscription Service! This is a test message."
    
    print("=" * 70)
    print("SENDING SMS TO BANGLADESHI NUMBER")
    print("=" * 70)
    print(f"\nPhone: {phone_number}")
    print(f"Message: {message}")
    print("\n" + "-" * 70)
    
    # Try to send
    success = send_sms_direct(phone_number, message)
    
    if not success:
        print("\n[INFO] Trying alternative method...")
        send_via_smtp_test(phone_number, message)
    
    print("\n" + "=" * 70)
    
    if success:
        print("[SUCCESS] Message sent!")
    else:
        print("[INFO] Message not sent. Please configure SMS API service.")
        print("\nRecommended: Use Twilio for international SMS")
        print("Install: pip install twilio")
        print("Docs: https://www.twilio.com/docs/sms/quickstart/python")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

