#!/usr/bin/env python3
"""
Clear all data from the database
This script will delete all records from all tables
"""

from flask import Flask
from config import Config
from models import db, Subscriber, ScheduledMessage, Subscription, DepositApproval

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def clear_all_data():
    """Clear all data from all tables."""
    with app.app_context():
        print("⚠️  WARNING: This will delete ALL data from the database!")
        print("\nTables that will be cleared:")
        print("  - Subscribers")
        print("  - Scheduled Messages")
        print("  - Subscriptions")
        print("  - Deposit Approvals")
        
        confirm = input("\nAre you sure you want to continue? (type 'yes' to confirm): ")
        
        if confirm.lower() != 'yes':
            print("❌ Operation cancelled.")
            return
        
        try:
            # Count records before deletion
            subscriber_count = Subscriber.query.count()
            message_count = ScheduledMessage.query.count()
            subscription_count = Subscription.query.count()
            deposit_count = DepositApproval.query.count()
            
            print(f"\n📊 Current data:")
            print(f"  - Subscribers: {subscriber_count}")
            print(f"  - Scheduled Messages: {message_count}")
            print(f"  - Subscriptions: {subscription_count}")
            print(f"  - Deposit Approvals: {deposit_count}")
            
            # Delete all records
            print("\n🗑️  Deleting data...")
            
            ScheduledMessage.query.delete()
            DepositApproval.query.delete()
            Subscription.query.delete()
            Subscriber.query.delete()
            
            db.session.commit()
            
            print("✅ All data cleared successfully!")
            print("\n📊 Remaining records:")
            print(f"  - Subscribers: {Subscriber.query.count()}")
            print(f"  - Scheduled Messages: {ScheduledMessage.query.count()}")
            print(f"  - Subscriptions: {Subscription.query.count()}")
            print(f"  - Deposit Approvals: {DepositApproval.query.count()}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing data: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    clear_all_data()

