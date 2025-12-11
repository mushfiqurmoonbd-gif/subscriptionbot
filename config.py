import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    # Railway provides DATABASE_URL automatically for PostgreSQL
    # SQLite fallback for local development
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        # Convert postgres:// to postgresql:// for SQLAlchemy
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///subscription_service.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Stripe
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    STRIPE_PRICE_ID = os.environ.get('STRIPE_PRICE_ID')  # Optional: Pre-created price ID
    
    # PayPal
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
    PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET')
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # sandbox or live
    PAYPAL_WEBHOOK_ID = os.environ.get('PAYPAL_WEBHOOK_ID')
    
    # Coinbase Commerce (Cryptocurrency)
    COINBASE_COMMERCE_API_KEY = os.environ.get('COINBASE_COMMERCE_API_KEY')
    COINBASE_COMMERCE_WEBHOOK_SECRET = os.environ.get('COINBASE_COMMERCE_WEBHOOK_SECRET')
    
    # Cryptocurrency (Manual tracking)
    CRYPTO_WALLETS = {
        'BTC': os.environ.get('BTC_WALLET_ADDRESS'),
        'ETH': os.environ.get('ETH_WALLET_ADDRESS'),
        'USDC': os.environ.get('USDC_WALLET_ADDRESS'),
        'USDT': os.environ.get('USDT_WALLET_ADDRESS'),
    }
    
    # Subscription
    MONTHLY_PRICE = 1.60  # $1.60 per month
    
    # Email/SMS Configuration
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL')
    
    # Server
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    # Support Contact (default, can be overridden per group)
    SUPPORT_TELEGRAM_USERNAME = os.environ.get('SUPPORT_TELEGRAM_USERNAME', '')  # e.g., "@admin" or "admin"
    SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', '')  # Support email address
    
    # Default Start Message (can be overridden per group)
    DEFAULT_START_MESSAGE = os.environ.get('DEFAULT_START_MESSAGE', 
        "👋 Welcome to the Subscription Service Bot!\n\n"
        "I'll help you subscribe to our SMS service.\n\n"
        "Please provide your information:\n"
        "📱 **Step 1:** Send your 10-digit phone number (e.g., 1234567890)")
    
    # Default Group ID (for single-group setups, can be None for multi-group)
    DEFAULT_GROUP_ID = os.environ.get('DEFAULT_GROUP_ID')  # Can be None or a group ID
    
    # Twilio SMS API (for international SMS, including Bangladesh)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

