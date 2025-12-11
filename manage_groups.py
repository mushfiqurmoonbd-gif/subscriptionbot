"""
Script to manage service groups
Allows creating and managing multiple groups/services on the same website
"""
from app import app
from models import db, ServiceGroup, SubscriptionPlan
import json

def create_group(name, description, start_message, support_telegram=None, support_email=None, default_plan_id=None, scheduled_times=None):
    """Create a new service group."""
    with app.app_context():
        # Check if group already exists
        existing = ServiceGroup.query.filter_by(name=name).first()
        if existing:
            print(f"❌ Group '{name}' already exists!")
            return None
        
        # Create group
        group = ServiceGroup(
            name=name,
            description=description,
            start_message=start_message,
            support_telegram_username=support_telegram,
            support_email=support_email,
            default_plan_id=default_plan_id,
            scheduled_times=json.dumps(scheduled_times) if scheduled_times else None,
            is_active=True
        )
        
        db.session.add(group)
        db.session.commit()
        
        print(f"✅ Created group: {name} (ID: {group.id})")
        return group

def list_groups():
    """List all service groups."""
    with app.app_context():
        groups = ServiceGroup.query.all()
        if not groups:
            print("No groups found.")
            return
        
        print("\n📋 Service Groups:")
        print("-" * 60)
        for group in groups:
            status = "✅ Active" if group.is_active else "❌ Inactive"
            print(f"\nID: {group.id}")
            print(f"Name: {group.name}")
            print(f"Status: {status}")
            if group.description:
                print(f"Description: {group.description}")
            if group.support_telegram_username:
                print(f"Support Telegram: {group.support_telegram_username}")
            if group.support_email:
                print(f"Support Email: {group.support_email}")
            if group.scheduled_times:
                try:
                    times = json.loads(group.scheduled_times)
                    print(f"Scheduled Times: {times}")
                except:
                    pass

def update_group(group_id, **kwargs):
    """Update a service group."""
    with app.app_context():
        group = ServiceGroup.query.get(group_id)
        if not group:
            print(f"❌ Group with ID {group_id} not found!")
            return None
        
        # Update fields
        if 'name' in kwargs:
            group.name = kwargs['name']
        if 'description' in kwargs:
            group.description = kwargs['description']
        if 'start_message' in kwargs:
            group.start_message = kwargs['start_message']
        if 'support_telegram' in kwargs:
            group.support_telegram_username = kwargs['support_telegram']
        if 'support_email' in kwargs:
            group.support_email = kwargs['support_email']
        if 'default_plan_id' in kwargs:
            group.default_plan_id = kwargs['default_plan_id']
        if 'scheduled_times' in kwargs:
            group.scheduled_times = json.dumps(kwargs['scheduled_times']) if kwargs['scheduled_times'] else None
        if 'is_active' in kwargs:
            group.is_active = kwargs['is_active']
        
        db.session.commit()
        print(f"✅ Updated group: {group.name} (ID: {group.id})")
        return group

def create_example_motivational_group():
    """Create an example motivational group with morning/noon/evening messages."""
    start_message = (
        "👋 Welcome to the Motivational Group!\n\n"
        "Get daily motivational messages at:\n"
        "• 🌅 Morning (8:00 AM)\n"
        "• ☀️ Noon (12:00 PM)\n"
        "• 🌆 Evening (6:00 PM)\n\n"
        "Messages will be matched to your timezone!\n\n"
        "Please provide your information:\n"
        "📱 **Step 1:** Send your 10-digit phone number (e.g., 1234567890)"
    )
    
    scheduled_times = {
        "morning": "08:00",
        "noon": "12:00",
        "evening": "18:00"
    }
    
    return create_group(
        name="Motivational Group",
        description="Daily motivational messages at morning, noon, and evening",
        start_message=start_message,
        support_telegram="admin",  # Change this to your Telegram username
        support_email="support@example.com",  # Change this to your email
        scheduled_times=scheduled_times
    )

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_groups.py list")
        print("  python manage_groups.py create_example")
        print("  python manage_groups.py create <name> <description> <start_message>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'list':
        list_groups()
    elif command == 'create_example':
        create_example_motivational_group()
    elif command == 'create':
        if len(sys.argv) < 5:
            print("Usage: python manage_groups.py create <name> <description> <start_message>")
            sys.exit(1)
        name = sys.argv[2]
        description = sys.argv[3]
        start_message = sys.argv[4]
        create_group(name, description, start_message)
    else:
        print(f"Unknown command: {command}")

