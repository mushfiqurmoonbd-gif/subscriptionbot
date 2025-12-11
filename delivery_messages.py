"""
Delivery Message Templates for Clients
These templates can be used when sending SMS to subscribers
"""

# Welcome/Activation Messages
WELCOME_MESSAGE = """Welcome! Your subscription is now active. You'll receive regular updates via SMS. Thank you for subscribing!"""

ACTIVATION_MESSAGE = """✅ Your subscription has been activated successfully! You'll now receive regular SMS updates. Thank you!"""

# Payment Confirmation Messages
PAYMENT_CONFIRMED = """✅ Payment received! Your subscription is now active. You'll receive regular SMS updates. Thank you!"""

PAYMENT_APPROVED = """✅ Your payment has been approved! Your subscription is now active. Thank you for your patience."""

# Service Delivery Messages
SERVICE_ACTIVE = """🎉 Great news! Your subscription service is now active. You'll receive regular updates via SMS. Thank you for choosing us!"""

DELIVERY_CONFIRMED = """✅ Your service has been delivered and activated. You'll receive regular SMS updates. Thank you for subscribing!"""

# Customizable Template
def create_delivery_message(
    subscriber_name=None,
    service_name="Subscription Service",
    subscription_duration="monthly",
    support_contact=None
):
    """
    Create a personalized delivery message.
    
    Args:
        subscriber_name: Name of the subscriber (optional)
        service_name: Name of the service
        subscription_duration: Duration of subscription
        support_contact: Support contact info (optional)
    
    Returns:
        str: Formatted delivery message
    """
    greeting = f"Hi {subscriber_name}!" if subscriber_name else "Hello!"
    
    message = f"""{greeting}

✅ Your {service_name} subscription is now active!

📅 Duration: {subscription_duration}
📱 You'll receive regular updates via SMS

Thank you for subscribing!"""
    
    if support_contact:
        message += f"\n\nNeed help? Contact: {support_contact}"
    
    return message

# Bengali Delivery Messages
WELCOME_MESSAGE_BN = """স্বাগতম! আপনার subscription এখন active। আপনি regular SMS updates পাবেন। ধন্যবাদ!"""

ACTIVATION_MESSAGE_BN = """✅ আপনার subscription সফলভাবে activate করা হয়েছে! আপনি এখন regular SMS updates পাবেন। ধন্যবাদ!"""

PAYMENT_CONFIRMED_BN = """✅ Payment গ্রহণ করা হয়েছে! আপনার subscription এখন active। আপনি regular SMS updates পাবেন। ধন্যবাদ!"""

PAYMENT_APPROVED_BN = """✅ আপনার payment approve করা হয়েছে! আপনার subscription এখন active। আপনার ধৈর্যের জন্য ধন্যবাদ।"""

# Professional Delivery Template
PROFESSIONAL_DELIVERY = """Dear Customer,

Your subscription has been successfully activated.

Service: {service_name}
Status: Active
Start Date: {start_date}

You will receive regular updates via SMS.

Thank you for choosing our service!

Best regards,
Support Team"""

# Simple Delivery Template
SIMPLE_DELIVERY = """✅ Subscription Activated!

Your service is now active. You'll receive regular SMS updates.

Thank you!"""

# Friendly Delivery Template
FRIENDLY_DELIVERY = """🎉 Welcome aboard!

Your subscription is now active. Get ready for regular updates delivered straight to your phone.

Thank you for subscribing!"""

# Get message by type
def get_delivery_message(message_type='welcome', language='en', **kwargs):
    """
    Get delivery message by type.
    
    Args:
        message_type: 'welcome', 'activation', 'payment_confirmed', 'custom'
        language: 'en' or 'bn'
        **kwargs: Additional parameters for custom messages
    
    Returns:
        str: Delivery message
    """
    messages = {
        'en': {
            'welcome': WELCOME_MESSAGE,
            'activation': ACTIVATION_MESSAGE,
            'payment_confirmed': PAYMENT_CONFIRMED,
            'payment_approved': PAYMENT_APPROVED,
            'service_active': SERVICE_ACTIVE,
            'delivery_confirmed': DELIVERY_CONFIRMED,
            'simple': SIMPLE_DELIVERY,
            'friendly': FRIENDLY_DELIVERY,
            'professional': PROFESSIONAL_DELIVERY.format(
                service_name=kwargs.get('service_name', 'Subscription Service'),
                start_date=kwargs.get('start_date', 'Today')
            )
        },
        'bn': {
            'welcome': WELCOME_MESSAGE_BN,
            'activation': ACTIVATION_MESSAGE_BN,
            'payment_confirmed': PAYMENT_CONFIRMED_BN,
            'payment_approved': PAYMENT_APPROVED_BN,
        }
    }
    
    if message_type == 'custom':
        return create_delivery_message(**kwargs)
    
    return messages.get(language, messages['en']).get(
        message_type, 
        WELCOME_MESSAGE
    )

# Example usage
if __name__ == '__main__':
    print("=== Delivery Message Examples ===\n")
    
    print("1. Welcome Message (English):")
    print(get_delivery_message('welcome', 'en'))
    print("\n" + "="*50 + "\n")
    
    print("2. Activation Message (Bengali):")
    print(get_delivery_message('activation', 'bn'))
    print("\n" + "="*50 + "\n")
    
    print("3. Custom Message:")
    print(create_delivery_message(
        subscriber_name="John Doe",
        service_name="SMS Subscription",
        subscription_duration="monthly",
        support_contact="support@example.com"
    ))
    print("\n" + "="*50 + "\n")
    
    print("4. Professional Message:")
    print(get_delivery_message(
        'professional',
        service_name="Premium SMS Service",
        start_date="2024-11-06"
    ))

