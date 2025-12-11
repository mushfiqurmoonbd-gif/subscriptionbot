"""
Send SMS to Bangladeshi number using Twilio
This is the recommended method for sending SMS to international numbers.

Setup:
1. Sign up at https://www.twilio.com/
2. Get Account SID, Auth Token, and buy a phone number
3. Add to .env:
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
4. Install: pip install twilio
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def send_sms_via_twilio(phone_number, message):
    """Send SMS using Twilio API."""
    try:
        from twilio.rest import Client
        
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if not account_sid or not auth_token or not twilio_number:
            print("[ERROR] Twilio not configured!")
            print("\nPlease add to .env file:")
            print("TWILIO_ACCOUNT_SID=your_account_sid")
            print("TWILIO_AUTH_TOKEN=your_auth_token")
            print("TWILIO_PHONE_NUMBER=+1234567890")
            return False
        
        client = Client(account_sid, auth_token)
        
        print(f"[INFO] Sending SMS to {phone_number}...")
        message_obj = client.messages.create(
            body=message,
            from_=twilio_number,
            to=phone_number
        )
        
        print(f"[OK] SMS sent successfully!")
        print(f"[OK] Message SID: {message_obj.sid}")
        print(f"[OK] Status: {message_obj.status}")
        return True
        
    except ImportError:
        print("[ERROR] Twilio not installed!")
        print("\nInstall with: pip install twilio")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to send SMS: {e}")
        return False

def main():
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    phone_number = "+8801701259687"
    message = "Hello! This is a test message from Subscription Service."
    
    print("=" * 70)
    print("SENDING SMS TO BANGLADESHI NUMBER VIA TWILIO")
    print("=" * 70)
    print(f"\nTo: {phone_number}")
    print(f"Message: {message}")
    print("\n" + "-" * 70)
    
    success = send_sms_via_twilio(phone_number, message)
    
    print("\n" + "=" * 70)
    
    if success:
        print("[SUCCESS] Message sent via Twilio!")
    else:
        print("[INFO] Please configure Twilio in .env file")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

