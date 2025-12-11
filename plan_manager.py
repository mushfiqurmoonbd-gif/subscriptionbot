"""
Plan and Discount Code Management Utilities
"""
from datetime import datetime, timedelta
from models import db, SubscriptionPlan, DiscountCode

def get_active_plans():
    """Get all active subscription plans ordered by display_order."""
    return SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.display_order).all()

def get_plan_by_id(plan_id):
    """Get a subscription plan by ID."""
    return SubscriptionPlan.query.get(plan_id)

def get_plan_by_name(plan_name):
    """Get a subscription plan by name."""
    return SubscriptionPlan.query.filter_by(name=plan_name, is_active=True).first()

def create_default_plans():
    """Create default subscription plans if none exist."""
    if SubscriptionPlan.query.count() == 0:
        default_plans = [
            SubscriptionPlan(
                name="Basic",
                description="Basic subscription plan",
                price=1.60,
                currency="USD",
                has_trial=False,
                trial_days=0,
                is_active=True,
                display_order=1
            ),
            SubscriptionPlan(
                name="Premium",
                description="Premium subscription plan",
                price=2.99,
                currency="USD",
                has_trial=True,
                trial_days=7,
                is_active=True,
                display_order=2
            ),
            SubscriptionPlan(
                name="Pro",
                description="Professional subscription plan",
                price=4.99,
                currency="USD",
                has_trial=True,
                trial_days=14,
                is_active=True,
                display_order=3
            ),
        ]
        
        for plan in default_plans:
            db.session.add(plan)
        
        db.session.commit()
        print("✅ Default subscription plans created!")
        return default_plans
    return []

def validate_discount_code(code, plan_id=None):
    """
    Validate a discount code.
    
    Args:
        code: Discount code string
        plan_id: Optional plan ID to check applicability
    
    Returns:
        tuple: (is_valid, discount_code_obj, error_message)
    """
    discount_code = DiscountCode.query.filter_by(code=code.upper()).first()
    
    if not discount_code:
        return False, None, "Discount code not found"
    
    is_valid, error_msg = discount_code.is_valid(plan_id)
    
    if not is_valid:
        return False, discount_code, error_msg
    
    return True, discount_code, None

def apply_discount_code(discount_code, plan):
    """
    Apply discount code to a plan and return pricing details.
    
    Args:
        discount_code: DiscountCode instance
        plan: SubscriptionPlan instance
    
    Returns:
        dict: {
            'base_price': float,
            'discount_percent': float or None,
            'discount_amount': float,
            'final_price': float,
            'is_free': bool
        }
    """
    base_price = float(plan.price) if plan.price else 0
    final_price, discount_amount = discount_code.apply_discount(base_price)
    
    discount_percent = None
    if discount_code.discount_type == 'percent':
        discount_percent = float(discount_code.discount_value)
    
    return {
        'base_price': base_price,
        'discount_percent': discount_percent,
        'discount_amount': discount_amount,
        'final_price': final_price,
        'is_free': final_price == 0
    }

def increment_discount_code_usage(discount_code):
    """Increment the usage count of a discount code."""
    discount_code.current_uses += 1
    db.session.commit()

def get_default_plan():
    """Get the default plan (lowest display_order active plan)."""
    return SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.display_order).first()

