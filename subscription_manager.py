import stripe
from datetime import datetime, timedelta
from flask import current_app
from config import Config
from models import db, Subscriber, Subscription
from plan_manager import get_default_plan

# Initialize Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

def create_stripe_customer(subscriber):
    """
    Create a Stripe customer for a subscriber.
    
    Args:
        subscriber: Subscriber model instance
    
    Returns:
        stripe.Customer object
    """
    customer = stripe.Customer.create(
        email=subscriber.email,
        metadata={
            'phone_number': subscriber.phone_number,
            'subscriber_id': subscriber.id
        }
    )
    
    subscriber.stripe_customer_id = customer.id
    db.session.commit()
    
    return customer

def create_subscription(subscriber, plan=None, final_price=None):
    """
    Create a Stripe subscription for a subscriber.
    
    Args:
        subscriber: Subscriber model instance
        plan: SubscriptionPlan instance (optional, uses subscriber's plan if not provided)
        final_price: Final price after discount (optional, uses plan price if not provided)
    
    Returns:
        stripe.Subscription object
    """
    if not subscriber.stripe_customer_id:
        create_stripe_customer(subscriber)
    
    # Get plan
    if not plan:
        plan = subscriber.plan if subscriber.plan_id else get_default_plan()
        if not plan:
            raise ValueError("No subscription plan found. Please create a plan first.")
    
    # Use final price if provided, otherwise use plan price
    price_to_use = final_price if final_price is not None else float(plan.price)
    
    # Handle free trial
    trial_period_days = None
    if plan.has_trial and plan.trial_days > 0:
        trial_period_days = plan.trial_days
        subscriber.is_trial = True
        subscriber.trial_start_date = datetime.utcnow()
        subscriber.trial_end_date = datetime.utcnow() + timedelta(days=plan.trial_days)
    
    # Create price ID (you'll need to create this in Stripe dashboard first)
    # For now, we'll use a one-time approach or create price on the fly
    price_id = getattr(Config, 'STRIPE_PRICE_ID', None)
    
    if price_id:
        # Use existing price ID from config
        price = {'id': price_id}
    else:
        # Create price on the fly
        try:
            price = stripe.Price.create(
                unit_amount=int(price_to_use * 100),  # Convert to cents
                currency='usd',
                recurring={'interval': 'month'},
                product_data={'name': f'{plan.name} Subscription'}
            )
        except Exception as e:
            raise ValueError(f"Failed to create Stripe price: {str(e)}. Please create a price in Stripe dashboard or set STRIPE_PRICE_ID environment variable.")
    
    # Create subscription with payment collection setup
    subscription_params = {
        'customer': subscriber.stripe_customer_id,
        'items': [{'price': price.id}],
        'payment_behavior': 'default_incomplete',  # Allows payment collection later
        'payment_settings': {'save_default_payment_method': 'on_subscription'},
        'expand': ['latest_invoice.payment_intent'],
        'metadata': {
            'subscriber_id': subscriber.id,
            'phone_number': subscriber.phone_number,
            'plan_id': plan.id,
            'plan_name': plan.name
        }
    }
    
    # Add trial period if applicable
    if trial_period_days:
        subscription_params['trial_period_days'] = trial_period_days
    
    subscription = stripe.Subscription.create(**subscription_params)
    
    # Update subscriber
    subscriber.stripe_subscription_id = subscription.id
    subscriber.subscription_status = subscription.status
    
    # Create subscription record
    sub_record = Subscription(
        subscriber_id=subscriber.id,
        payment_method='stripe',
        stripe_subscription_id=subscription.id,
        stripe_customer_id=subscriber.stripe_customer_id,
        status=subscription.status,
        current_period_start=datetime.fromtimestamp(subscription.current_period_start),
        current_period_end=datetime.fromtimestamp(subscription.current_period_end)
    )
    db.session.add(sub_record)
    db.session.commit()
    
    return subscription

def cancel_subscription(subscriber):
    """
    Cancel a subscriber's subscription.
    
    Args:
        subscriber: Subscriber model instance
    
    Returns:
        stripe.Subscription object (canceled)
    """
    if not subscriber.stripe_subscription_id:
        return None
    
    subscription = stripe.Subscription.modify(
        subscriber.stripe_subscription_id,
        cancel_at_period_end=True
    )
    
    subscriber.subscription_status = 'canceled'
    db.session.commit()
    
    return subscription

def handle_stripe_webhook(event):
    """
    Handle Stripe webhook events.
    
    Args:
        event: Stripe event object
    
    Returns:
        dict: Response
    """
    if event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        subscriber = Subscriber.query.filter_by(
            stripe_subscription_id=subscription['id']
        ).first()
        
        if subscriber:
            subscriber.subscription_status = subscription['status']
            db.session.commit()
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        subscriber = Subscriber.query.filter_by(
            stripe_subscription_id=subscription['id']
        ).first()
        
        if subscriber:
            subscriber.subscription_status = 'canceled'
            db.session.commit()
    
    return {'status': 'success'}

