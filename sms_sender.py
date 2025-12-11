import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import os
from flask import current_app
from config import Config

def send_sms_via_email(phone_number, carrier, message, smtp_config=None, image_path=None, image_url=None):
    """
    Send SMS message via email-to-SMS gateway.
    Supports text messages and optionally images (MMS via email).
    
    Args:
        phone_number: 10-digit phone number
        carrier: Carrier name
        message: Message text to send
        smtp_config: Optional SMTP config dict, otherwise uses Config
        image_path: Optional path to local image file to attach
        image_url: Optional URL to image (will send as link in message if image_path not provided)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        from email_sms_gateways import get_sms_email
        
        # Get SMS email address
        sms_email = get_sms_email(phone_number, carrier)
        
        # Get SMTP configuration
        if smtp_config is None:
            smtp_config = {
                'server': Config.SMTP_SERVER,
                'port': Config.SMTP_PORT,
                'username': Config.SMTP_USERNAME,
                'password': Config.SMTP_PASSWORD,
                'from_email': Config.SMTP_FROM_EMAIL or Config.SMTP_USERNAME
            }
        
        # Validate SMTP configuration
        if not smtp_config.get('username') or not smtp_config.get('password'):
            print("[ERROR] SMTP_USERNAME or SMTP_PASSWORD not configured")
            return False
        
        if not smtp_config.get('server'):
            print("[ERROR] SMTP_SERVER not configured")
            return False
        
        print(f"[INFO] Sending SMS via email to {sms_email} (carrier: {carrier})")
        print(f"[INFO] Using SMTP server: {smtp_config['server']}:{smtp_config['port']}")
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = smtp_config['from_email']
        msg['To'] = sms_email
        msg['Subject'] = ''  # SMS via email usually doesn't need subject
        
        # Add message body
        message_text = message
        
        # If image_url provided but no image_path, add URL to message
        if image_url and not image_path:
            message_text += f"\n\n📷 Image: {image_url}"
        
        msg.attach(MIMEText(message_text, 'plain'))
        
        # Attach image if provided
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as img_file:
                    img_data = img_file.read()
                    img = MIMEImage(img_data)
                    img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
                    msg.attach(img)
                print(f"[INFO] Image attached: {image_path}")
            except Exception as e:
                print(f"[WARNING] Could not attach image: {e}")
                # Continue without image
        
        # Send email via SMTP
        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
            server.starttls()
            server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
        
        print(f"[SUCCESS] SMS sent successfully to {phone_number} via {carrier}")
        return True
    
    except smtplib.SMTPAuthenticationError as e:
        print(f"[ERROR] SMTP Authentication failed: {str(e)}")
        print("[FIX] Check your SMTP_USERNAME and SMTP_PASSWORD in .env file")
        print("[FIX] For Gmail, make sure you're using an App Password, not your regular password")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        print(f"[ERROR] Recipient refused: {str(e)}")
        print(f"[INFO] SMS email address: {sms_email}")
        return False
    except smtplib.SMTPServerDisconnected as e:
        print(f"[ERROR] SMTP server disconnected: {str(e)}")
        print("[FIX] Check your network connection and SMTP server settings")
        return False
    except Exception as e:
        print(f"[ERROR] Error sending SMS via email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def send_sms_via_twilio(phone_number, message, image_url=None):
    """
    Send SMS/MMS using Twilio API (for international numbers).
    
    Args:
        phone_number: Phone number with country code (e.g., +8801701259687)
        message: Message text to send
        image_url: Optional URL to image for MMS (must be publicly accessible)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException
        
        # Get credentials and strip whitespace
        account_sid = (Config.TWILIO_ACCOUNT_SID or '').strip()
        auth_token = (Config.TWILIO_AUTH_TOKEN or '').strip()
        twilio_number = (Config.TWILIO_PHONE_NUMBER or '').strip()
        
        # Validate credentials
        if not account_sid:
            print("[ERROR] TWILIO_ACCOUNT_SID is not set in .env file")
            return False
        
        if not auth_token:
            print("[ERROR] TWILIO_AUTH_TOKEN is not set in .env file")
            return False
        
        if not twilio_number:
            print("[ERROR] TWILIO_PHONE_NUMBER is not set in .env file")
            return False
        
        # Validate Account SID format (should start with AC)
        if not account_sid.startswith('AC'):
            print("[ERROR] Invalid TWILIO_ACCOUNT_SID format. Should start with 'AC'")
            print(f"[INFO] Current value: {account_sid[:10]}...")
            return False
        
        # Create Twilio client
        client = Client(account_sid, auth_token)
        
        # Validate phone number format
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number.lstrip('+')
        
        print(f"[INFO] Sending SMS to {phone_number} from {twilio_number}...")
        
        # Prepare message parameters
        message_params = {
            'body': message,
            'from_': twilio_number,
            'to': phone_number
        }
        
        # Add media URL if provided (Twilio MMS support)
        if image_url:
            message_params['media_url'] = [image_url]
            print(f"[INFO] Sending MMS with image: {image_url}")
        
        # Send message
        message_obj = client.messages.create(**message_params)
        
        print(f"[SUCCESS] SMS sent via Twilio!")
        print(f"[INFO] Message SID: {message_obj.sid}")
        print(f"[INFO] Status: {message_obj.status}")
        return True
        
    except ImportError:
        print("[ERROR] Twilio not installed. Install with: pip install twilio")
        return False
    except TwilioRestException as e:
        error_code = e.code
        error_msg = e.msg
        
        print(f"[ERROR] Twilio API Error (Code {error_code}): {error_msg}")
        
        if error_code == 20003:
            print("\n[FIX] Authentication failed. Please check:")
            print("  1. TWILIO_ACCOUNT_SID is correct (starts with 'AC')")
            print("  2. TWILIO_AUTH_TOKEN is correct")
            print("  3. No extra spaces or quotes in .env file")
            print("  4. Credentials are from your Twilio dashboard")
            print("\n[INFO] Get credentials from: https://console.twilio.com/")
        elif error_code == 21211:
            print(f"\n[FIX] Invalid phone number: {phone_number}")
            print("  1. Ensure number starts with + and country code")
            print("  2. Example: +8801701259687")
        elif error_code == 21608:
            print(f"\n[FIX] Invalid Twilio phone number: {twilio_number}")
            print("  1. Ensure TWILIO_PHONE_NUMBER is correct")
            print("  2. Number should be in E.164 format: +1234567890")
        
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error sending SMS via Twilio: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def send_sms_to_subscriber(subscriber, message, image_path=None, image_url=None):
    """
    Send SMS to a subscriber using their stored information.
    Supports both US carriers (email-to-SMS) and international numbers (Twilio).
    Supports text messages and images (MMS).
    
    Args:
        subscriber: Subscriber model instance
        message: Message text to send
        image_path: Optional path to local image file to attach
        image_url: Optional URL to image (for Twilio MMS or as link in email)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    phone_number = subscriber.phone_number
    
    # Check if it's an international number (starts with + or longer than 10 digits)
    if phone_number.startswith('+') or len(phone_number.replace('+', '').replace('-', '').replace(' ', '')) > 10:
        # Try Twilio for international SMS/MMS
        return send_sms_via_twilio(phone_number, message, image_url=image_url)
    else:
        # Use email-to-SMS for US numbers
        return send_sms_via_email(
            phone_number,
            subscriber.carrier,
            message,
            image_path=image_path,
            image_url=image_url
        )

