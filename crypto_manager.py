import coinbase_commerce
from coinbase_commerce.client import Client
from coinbase_commerce.webhook import Webhook
from datetime import datetime, timedelta
from flask import current_app, request
from config import Config
from models import db, Subscriber, Subscription
from plan_manager import get_default_plan
import hmac
import hashlib
import json

# Initialize Coinbase Commerce client
crypto_client = None
if Config.COINBASE_COMMERCE_API_KEY:
    crypto_client = Client(api_key=Config.COINBASE_COMMERCE_API_KEY)

def create_crypto_checkout(subscriber, plan=None, final_price=None):
    """
    Create a cryptocurrency payment checkout using Coinbase Commerce.
    
    Args:
        subscriber: Subscriber model instance
        plan: SubscriptionPlan instance (optional, uses subscriber's plan if not provided)
        final_price: Final price after discount (optional, uses plan price if not provided)
    
    Returns:
        dict: Checkout details with payment URL
    """
    if not crypto_client:
        raise ValueError("Coinbase Commerce API key not configured")
    
    # Get plan
    if not plan:
        plan = subscriber.plan if subscriber.plan_id else get_default_plan()
        if not plan:
            raise ValueError("No subscription plan found. Please create a plan first.")
    
    # Use final price if provided, otherwise use plan price
    price_to_use = final_price if final_price is not None else float(plan.price)
    
    checkout = crypto_client.checkout.create(
        name=f"{plan.name} Subscription - {subscriber.phone_number}",
        description=f"{plan.name} subscription for ${price_to_use}",
        pricing_type="fixed_price",
        local_price={
            "amount": str(price_to_use),
            "currency": "USD"
        },
        requested_info=["email", "name"],
        metadata={
            "subscriber_id": subscriber.id,
            "phone_number": subscriber.phone_number,
            "plan_id": plan.id,
            "plan_name": plan.name
        }
    )
    
    subscriber.crypto_payment_address = checkout.id
    subscriber.payment_method = 'crypto'
    subscriber.subscription_status = 'pending'
    db.session.commit()
    
    return {
        'id': checkout.id,
        'hosted_url': checkout.hosted_url,
        'code': checkout.code
    }

def verify_crypto_payment(checkout_id):
    """
    Verify a cryptocurrency payment status.
    
    Args:
        checkout_id: Coinbase Commerce checkout ID
    
    Returns:
        dict: Payment status
    """
    if not crypto_client:
        return None
    
    try:
        checkout = crypto_client.checkout.retrieve(checkout_id)
        return {
            'id': checkout.id,
            'status': checkout.timeline[-1].status if checkout.timeline else 'PENDING',
            'pricing': checkout.pricing
        }
    except Exception as e:
        return None

def activate_crypto_subscription(subscriber, transaction_hash=None):
    """
    Activate subscription after crypto payment is confirmed.
    
    Args:
        subscriber: Subscriber model instance
        transaction_hash: Optional transaction hash for manual verification
    
    Returns:
        Subscription object
    """
    subscriber.subscription_status = 'active'
    if transaction_hash:
        subscriber.crypto_transaction_hash = transaction_hash
    
    # Create subscription record
    sub_record = Subscription(
        subscriber_id=subscriber.id,
        payment_method='crypto',
        crypto_payment_id=subscriber.crypto_payment_address,
        crypto_transaction_hash=transaction_hash,
        status='active',
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30)
    )
    db.session.add(sub_record)
    db.session.commit()
    
    return sub_record

def handle_coinbase_webhook():
    """
    Handle Coinbase Commerce webhook events.
    
    Returns:
        dict: Response
    """
    if not Config.COINBASE_COMMERCE_WEBHOOK_SECRET:
        return {'error': 'Webhook secret not configured'}, 400
    
    signature = request.headers.get('X-CC-Webhook-Signature')
    payload = request.data
    
    # Verify webhook signature
    expected_signature = hmac.new(
        Config.COINBASE_COMMERCE_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_signature:
        return {'error': 'Invalid signature'}, 400
    
    try:
        event = json.loads(payload)
        event_type = event.get('type')
        checkout = event.get('data')
        
        if event_type == 'checkout:confirmed':
            checkout_id = checkout.get('id')
            subscriber = Subscriber.query.filter_by(
                crypto_payment_address=checkout_id
            ).first()
            
            if subscriber:
                activate_crypto_subscription(subscriber)
        
        elif event_type == 'charge:confirmed':
            # Handle charge confirmation
            metadata = checkout.get('metadata', {})
            subscriber_id = metadata.get('subscriber_id')
            
            if subscriber_id:
                subscriber = Subscriber.query.get(subscriber_id)
                if subscriber:
                    activate_crypto_subscription(subscriber)
        
        return {'status': 'success'}
    
    except Exception as e:
        return {'error': str(e)}, 400

def get_crypto_wallet_addresses():
    """
    Get cryptocurrency wallet addresses for manual payment.
    
    Returns:
        dict: Wallet addresses by currency
    """
    return {
        currency: address
        for currency, address in Config.CRYPTO_WALLETS.items()
        if address
    }

def get_available_crypto_currencies():
    """
    Get list of available cryptocurrency currencies that have wallet addresses configured.
    
    Returns:
        list: List of currency codes (e.g., ['BTC', 'ETH', 'USDC'])
    """
    return [
        currency
        for currency, address in Config.CRYPTO_WALLETS.items()
        if address
    ]

def create_manual_crypto_subscription(subscriber, currency='BTC', transaction_hash=None, plan=None, final_price=None):
    """
    Create a manual crypto subscription (for manual payment tracking).
    Creates a deposit approval request that requires admin approval.
    
    Args:
        subscriber: Subscriber model instance
        currency: Cryptocurrency type (BTC, ETH, USDC, USDT)
        transaction_hash: Optional transaction hash if user already provided it
        plan: SubscriptionPlan instance (optional, uses subscriber's plan if not provided)
        final_price: Final price after discount (optional, uses plan price if not provided)
    
    Returns:
        dict: Payment details
    """
    from models import DepositApproval
    
    # Get plan
    if not plan:
        plan = subscriber.plan if subscriber.plan_id else get_default_plan()
        if not plan:
            raise ValueError("No subscription plan found. Please create a plan first.")
    
    # Use final price if provided, otherwise use plan price
    price_to_use = final_price if final_price is not None else float(plan.price)
    
    wallet_address = Config.CRYPTO_WALLETS.get(currency)
    
    if not wallet_address:
        env_var_name = f"{currency}_WALLET_ADDRESS"
        raise ValueError(
            f"No wallet address configured for {currency}.\n"
            f"Please set the {env_var_name} environment variable in your .env file.\n"
            f"Example: {env_var_name}=your_{currency.lower()}_wallet_address\n"
            f"Alternatively, use Coinbase Commerce for automatic crypto payments."
        )
    
    subscriber.payment_method = 'crypto'
    subscriber.crypto_payment_address = wallet_address
    subscriber.subscription_status = 'pending'
    
    # Create deposit approval request
    deposit_approval = DepositApproval(
        subscriber_id=subscriber.id,
        currency=currency,
        amount=price_to_use,
        wallet_address=wallet_address,
        transaction_hash=transaction_hash,
        status='pending'
    )
    
    db.session.add(deposit_approval)
    db.session.commit()
    
    return {
        'currency': currency,
        'wallet_address': wallet_address,
        'amount': price_to_use,
        'status': 'pending_approval',
        'deposit_approval_id': deposit_approval.id,
        'plan_name': plan.name,
        'instructions': f'Send ${price_to_use} worth of {currency} to {wallet_address}. Payment will be verified by admin.'
    }

def verify_manual_crypto_payment(subscriber, transaction_hash):
    """
    Manually verify and activate crypto subscription after payment.
    
    Args:
        subscriber: Subscriber model instance
        transaction_hash: Transaction hash for verification
    
    Returns:
        Subscription object
    """
    return activate_crypto_subscription(subscriber, transaction_hash)

