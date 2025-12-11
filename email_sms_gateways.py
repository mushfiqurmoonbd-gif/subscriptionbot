"""
Email-to-SMS Gateway Mappings
Each carrier has a specific email domain format for sending SMS via email.
Format: [10-digit-phone-number]@[gateway-domain]
"""

EMAIL_SMS_GATEWAYS = {
    # Major US Carriers
    'att': 'txt.att.net',
    'verizon': 'vtext.com',
    't-mobile': 'tmomail.net',
    'sprint': 'messaging.sprintpcs.com',
    'boost': 'myboostmobile.com',
    'cricket': 'sms.cricketwireless.net',
    'metropcs': 'mymetropcs.com',
    'tracfone': 'mmst5.tracfone.com',
    'uscellular': 'email.uscc.net',
    'virgin': 'vmobl.com',
    'xfinity': 'vtext.com',
    
    # Additional Carriers
    'googlefi': 'msg.fi.google.com',
    'republic': 'text.republicwireless.com',
    'visible': 'vtext.com',
    'mint': 'tmomail.net',
    
    # International/Other
    'projectfi': 'msg.fi.google.com',
    'ting': 'message.ting.com',
    'consumercellular': 'mailmymobile.net',
    'straighttalk': 'vtext.com',
    'ultra': 'mymetropcs.com',
    'lycamobile': 'lycamobile.us',
    
    # Wireless and Paging Services
    
    # 3 River Wireless
    '3river': 'sms.3rivers.net',
    '3riverwireless': 'sms.3rivers.net',
    '3rivers': 'sms.3rivers.net',
    
    # ACS Wireless
    'acswireless': 'paging.acswireless.com',
    'acs': 'paging.acswireless.com',
    
    # Advantage Communications
    'advantage': 'advantagepaging.com',
    'advantagecommunications': 'advantagepaging.com',
    'advantagecomm': 'advantagepaging.com',
    
    # Airtouch Pagers (Multiple gateway formats)
    'airtouch': 'myairmail.com',
    'airtouchpagers': 'myairmail.com',
    'airtouchmyairmail': 'myairmail.com',
    'airtouchalphapage': 'alphapage.airtouch.com',
    'airtouchalpha': 'alphapage.airtouch.com',
    'airtouchnet': 'airtouch.net',
    'airtouchpaging': 'airtouchpaging.com',
    
    # AlphNow (Note: Uses PIN number, not 10-digit phone)
    'alphnow': 'alphanow.net',
    
    # Alltel
    'alltel': 'alltelmessage.com',
    'alltelmessage': 'alltelmessage.com',
    
    # Alltel PCS
    'alltelpcs': 'message.alltel.com',
    'alltelpcsmessage': 'message.alltel.com',
    
    # Ameritech Paging (Multiple gateway formats)
    'ameritechpaging': 'paging.acswireless.com',
    'ameritech': 'paging.acswireless.com',
    'ameritechpagingapi': 'pageapi.com',
    'ameritechapi': 'pageapi.com',
    
    # Ameritech Clearpath
    'ameritechclearpath': 'clearpath.acswireless.com',
    'ameritechclear': 'clearpath.acswireless.com',
}

def get_sms_email(phone_number, carrier):
    """
    Generate SMS email address from phone number and carrier.
    
    Args:
        phone_number: 10-digit phone number (string, digits only)
        carrier: Carrier name (lowercase, key from EMAIL_SMS_GATEWAYS)
    
    Returns:
        Email address string (e.g., '1234567890@myboostmobile.com')
    """
    # Clean phone number (remove non-digits)
    clean_phone = ''.join(filter(str.isdigit, phone_number))
    
    # Ensure it's 10 digits
    if len(clean_phone) != 10:
        raise ValueError(f"Phone number must be 10 digits, got {len(clean_phone)}")
    
    # Get carrier domain
    carrier_lower = carrier.lower()
    if carrier_lower not in EMAIL_SMS_GATEWAYS:
        raise ValueError(f"Unknown carrier: {carrier}. Available carriers: {', '.join(EMAIL_SMS_GATEWAYS.keys())}")
    
    gateway = EMAIL_SMS_GATEWAYS[carrier_lower]
    return f"{clean_phone}@{gateway}"

def list_available_carriers():
    """Return list of available carrier names."""
    return list(EMAIL_SMS_GATEWAYS.keys())

