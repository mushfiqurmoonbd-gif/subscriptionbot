"""
Database Migration Script
Creates default subscription plans and initializes the database
"""
from app import app
from models import db, SubscriptionPlan, DiscountCode
from plan_manager import create_default_plans

def init_database():
    """Initialize database with default plans."""
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create default plans if none exist
        plans = create_default_plans()
        
        print(f"✅ Database initialized!")
        print(f"✅ Created {len(plans)} default subscription plans")
        
        # List all plans
        all_plans = SubscriptionPlan.query.all()
        print("\n📋 Available Plans:")
        for plan in all_plans:
            trial_info = f" ({plan.trial_days} days trial)" if plan.has_trial else ""
            print(f"  - {plan.name}: ${plan.price}/month{trial_info}")

if __name__ == '__main__':
    init_database()

