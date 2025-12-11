import paypalrestsdk
import os
from datetime import datetime, timedelta
from flask import current_app
from config import Config
from models import db, Subscriber, Subscription
from plan_manager import get_default_plan

# Configure PayPal
paypalrestsdk.configure({
    "mode": Config.PAYPAL_MODE,
    "client_id": Config.PAYPAL_CLIENT_ID,
    "client_secret": Config.PAYPAL_CLIENT_SECRET
})

def create_paypal_billing_plan(plan=None, final_price=None):
    """
    Create a PayPal billing plan for subscriptions.
    
    Args:
        plan: SubscriptionPlan instance (optional)
        final_price: Final price after discount (optional)
    
    Returns:
        paypalrestsdk.BillingPlan object
    """
    if not plan:
        plan = get_default_plan()
        if not plan:
            raise ValueError("No subscription plan found. Please create a plan first.")
    
    price_to_use = final_price if final_price is not None else float(plan.price)
    
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    billing_plan = paypalrestsdk.BillingPlan({
        "name": f"{plan.name} Subscription Plan",
        "description": f"{plan.name} subscription for ${price_to_use}",
        "merchant_preferences": {
            "auto_bill_amount": "yes",
            "cancel_url": f"{base_url}/cancel",
            "initial_fail_amount_action": "continue",
            "max_fail_attempts": "3",
            "return_url": f"{base_url}/success",
            "setup_fee": {
                "currency": "USD",
                "value": "0"
            }
        },
        "payment_definitions": [{
            "amount": {
                "currency": "USD",
                "value": str(price_to_use)
            },
            "cycles": "0",  # 0 = infinite cycles
            "frequency": "Month",
            "frequency_interval": "1",
            "name": "Monthly Payment",
            "type": "REGULAR"
        }],
        "type": "INFINITE"  # Recurring subscription
    })
    
    if billing_plan.create():
        # Activate the plan
        billing_plan.update({"state": "ACTIVE"})
        return billing_plan
    else:
        raise ValueError(f"Failed to create PayPal billing plan: {billing_plan.error}")
    
    return billing_plan

def create_paypal_subscription(subscriber, plan=None, final_price=None, plan_id=None):
    """
    Create a PayPal subscription for a subscriber.
    
    Args:
        subscriber: Subscriber model instance
        plan: SubscriptionPlan instance (optional)
        final_price: Final price after discount (optional)
        plan_id: PayPal billing plan ID (optional, will create if not provided)
    
    Returns:
        dict: Subscription details with approval URL
    """
    if not plan_id:
        # Create billing plan if not provided
        plan = plan or (subscriber.plan if subscriber.plan_id else get_default_plan())
        plan_obj = create_paypal_billing_plan(plan, final_price)
        plan_id = plan_obj.id
    
    price_to_use = final_price if final_price is not None else (float(plan.price) if plan else Config.MONTHLY_PRICE)
    
    billing_agreement = paypalrestsdk.BillingAgreement({
        "name": f"{plan.name if plan else 'Monthly'} Subscription",
        "description": f"{plan.name if plan else 'Monthly'} subscription for ${price_to_use}",
        "start_date": (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plan": {
            "id": plan_id
        },
        "payer": {
            "payment_method": "paypal"
        }
    })
    
    if billing_agreement.create():
        # Get approval URL
        approval_url = None
        for link in billing_agreement.links:
            if link.rel == "approval_url":
                approval_url = link.href
                break
        
        # Store billing agreement ID
        subscriber.paypal_billing_agreement_id = billing_agreement.id
        subscriber.payment_method = 'paypal'
        subscriber.subscription_status = 'pending'
        db.session.commit()
        
        return {
            'id': billing_agreement.id,
            'status': billing_agreement.state,
            'approval_url': approval_url
        }
    else:
        raise ValueError(f"Failed to create PayPal subscription: {billing_agreement.error}")

def execute_paypal_agreement(subscriber, payer_id):
    """
    Execute a PayPal billing agreement after user approval.
    
    Args:
        subscriber: Subscriber model instance
        payer_id: Payer ID from PayPal approval
    
    Returns:
        paypalrestsdk.BillingAgreement object
    """
    if not subscriber.paypal_billing_agreement_id:
        raise ValueError("No billing agreement ID found for subscriber")
    
    billing_agreement = paypalrestsdk.BillingAgreement.find(subscriber.paypal_billing_agreement_id)
    
    if billing_agreement.execute({"payer_id": payer_id}):
        subscriber.paypal_subscription_id = billing_agreement.id
        subscriber.subscription_status = 'active'
        
        # Create or update subscription record
        sub_record = Subscription.query.filter_by(
            subscriber_id=subscriber.id,
            payment_method='paypal'
        ).first()
        
        if not sub_record:
            sub_record = Subscription(
                subscriber_id=subscriber.id,
                payment_method='paypal',
                paypal_subscription_id=billing_agreement.id,
                paypal_billing_agreement_id=billing_agreement.id,
                status=billing_agreement.state,
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(sub_record)
        else:
            sub_record.paypal_subscription_id = billing_agreement.id
            sub_record.paypal_billing_agreement_id = billing_agreement.id
            sub_record.status = billing_agreement.state
            sub_record.current_period_start = datetime.utcnow()
            sub_record.current_period_end = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()
        return billing_agreement
    else:
        raise ValueError(f"Failed to execute PayPal agreement: {billing_agreement.error}")

def cancel_paypal_subscription(subscriber):
    """
    Cancel a PayPal subscription.
    
    Args:
        subscriber: Subscriber model instance
    
    Returns:
        bool: True if canceled successfully
    """
    if not subscriber.paypal_subscription_id:
        return False
    
    billing_agreement = paypalrestsdk.BillingAgreement.find(subscriber.paypal_subscription_id)
    
    # Cancel the agreement
    cancel_note = {
        "note": "Subscription canceled by user"
    }
    
    if billing_agreement.cancel(cancel_note):
        subscriber.subscription_status = 'canceled'
        db.session.commit()
        return True
    else:
        return False

def handle_paypal_webhook(event_type, resource):
    """
    Handle PayPal webhook events.
    
    Args:
        event_type: PayPal event type
        resource: PayPal resource data
    
    Returns:
        dict: Response
    """
    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        billing_agreement_id = resource.get('id')
        subscriber = Subscriber.query.filter_by(
            paypal_billing_agreement_id=billing_agreement_id
        ).first()
        
        if subscriber:
            subscriber.subscription_status = 'active'
            subscriber.paypal_subscription_id = billing_agreement_id
            db.session.commit()
    
    elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
        billing_agreement_id = resource.get('id')
        subscriber = Subscriber.query.filter_by(
            paypal_subscription_id=billing_agreement_id
        ).first()
        
        if subscriber:
            subscriber.subscription_status = 'canceled'
            db.session.commit()
    
    elif event_type == "BILLING.SUBSCRIPTION.PAYMENT.FAILED":
        billing_agreement_id = resource.get('billing_agreement_id')
        subscriber = Subscriber.query.filter_by(
            paypal_subscription_id=billing_agreement_id
        ).first()
        
        if subscriber:
            subscriber.subscription_status = 'past_due'
            db.session.commit()
    
    return {'status': 'success'}

