"""
Database Migration Script
Adds new columns to subscribers table and creates new tables for plans and discount codes
"""
from app import app
from models import db, SubscriptionPlan, DiscountCode, ServiceGroup
from sqlalchemy import text

def migrate_database():
    """Migrate database to add new columns and tables."""
    with app.app_context():
        print("🔄 Starting database migration...")
        
        # Check if migration is needed
        inspector = db.inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('subscribers')]
        
        # Columns to add
        new_columns = {
            'plan_id': 'INTEGER',
            'discount_code_id': 'INTEGER',
            'applied_discount_percent': 'NUMERIC(5, 2)',
            'final_price': 'NUMERIC(10, 2)',
            'is_trial': 'BOOLEAN DEFAULT 0',
            'trial_start_date': 'DATETIME',
            'trial_end_date': 'DATETIME',
            'timezone_offset_minutes': 'INTEGER',
            'timezone_label': "TEXT DEFAULT 'UTC'",
            'message_delivery_preference': "TEXT DEFAULT 'scheduled'",
            'use_timezone_matching': 'INTEGER DEFAULT 0',
            'group_id': 'INTEGER'
        }
        
        # Add missing columns to subscribers table
        columns_to_add = {k: v for k, v in new_columns.items() if k not in existing_columns}
        
        if columns_to_add:
            print(f"\n📝 Adding {len(columns_to_add)} new columns to subscribers table...")
            for col_name, col_type in columns_to_add.items():
                try:
                    if col_type.startswith('NUMERIC'):
                        # SQLite doesn't support NUMERIC directly, use REAL
                        sql_type = 'REAL'
                    elif col_type.startswith('BOOLEAN'):
                        sql_type = 'INTEGER DEFAULT 0'
                    elif col_type.startswith('DATETIME'):
                        sql_type = 'DATETIME'
                    elif col_type.startswith('TEXT'):
                        sql_type = 'TEXT'
                    elif col_type.startswith('INTEGER'):
                        sql_type = 'INTEGER'
                    else:
                        sql_type = col_type
                    
                    # SQLite doesn't support ALTER TABLE ADD COLUMN with constraints easily
                    # So we'll use a simpler approach
                    if 'DEFAULT' in sql_type:
                        default_value = sql_type.split('DEFAULT')[1].strip()
                        sql_type = sql_type.split('DEFAULT')[0].strip()
                        alter_sql = f"ALTER TABLE subscribers ADD COLUMN {col_name} {sql_type} DEFAULT {default_value}"
                    else:
                        alter_sql = f"ALTER TABLE subscribers ADD COLUMN {col_name} {sql_type}"
                    
                    db.session.execute(text(alter_sql))
                    print(f"  ✅ Added column: {col_name}")
                except Exception as e:
                    print(f"  ⚠️  Column {col_name} might already exist: {e}")
            
            db.session.commit()
        else:
            print("✅ All columns already exist in subscribers table")
        
        # Ensure scheduled_messages table has timezone columns
        scheduled_columns = [col['name'] for col in inspector.get_columns('scheduled_messages')]
        scheduled_new_columns = {
            'timezone_offset_minutes': 'INTEGER',
            'timezone_label': "TEXT DEFAULT 'UTC'"
        }
        scheduled_to_add = {k: v for k, v in scheduled_new_columns.items() if k not in scheduled_columns}
        if scheduled_to_add:
            print(f"\n📝 Adding {len(scheduled_to_add)} new columns to scheduled_messages table...")
            for col_name, col_type in scheduled_to_add.items():
                try:
                    if col_type.startswith('INTEGER'):
                        sql_type = 'INTEGER'
                    elif col_type.startswith('TEXT'):
                        sql_type = 'TEXT'
                    else:
                        sql_type = col_type
                    
                    if 'DEFAULT' in col_type:
                        default_value = col_type.split('DEFAULT')[1].strip()
                        sql_type = sql_type.split('DEFAULT')[0].strip()
                        alter_sql = f"ALTER TABLE scheduled_messages ADD COLUMN {col_name} {sql_type} DEFAULT {default_value}"
                    else:
                        alter_sql = f"ALTER TABLE scheduled_messages ADD COLUMN {col_name} {sql_type}"
                    
                    db.session.execute(text(alter_sql))
                    print(f"  ✅ Added column: {col_name}")
                except Exception as e:
                    print(f"  ⚠️  Column {col_name} might already exist: {e}")
            db.session.commit()
        else:
            print("✅ All columns already exist in scheduled_messages table")
        
        # Create new tables if they don't exist
        existing_tables = inspector.get_table_names()
        
        if 'subscription_plans' not in existing_tables:
            print("\n📝 Creating subscription_plans table...")
            db.create_all()
            print("  ✅ Created subscription_plans table")
        else:
            print("✅ subscription_plans table already exists")
        
        if 'discount_codes' not in existing_tables:
            print("\n📝 Creating discount_codes table...")
            db.create_all()
            print("  ✅ Created discount_codes table")
        else:
            print("✅ discount_codes table already exists")
        
        if 'service_groups' not in existing_tables:
            print("\n📝 Creating service_groups table...")
            db.create_all()
            print("  ✅ Created service_groups table")
        else:
            print("✅ service_groups table already exists")
        
        # Create default plans if none exist
        if SubscriptionPlan.query.count() == 0:
            print("\n📝 Creating default subscription plans...")
            from plan_manager import create_default_plans
            plans = create_default_plans()
            print(f"  ✅ Created {len(plans)} default plans")
        else:
            print(f"✅ {SubscriptionPlan.query.count()} plans already exist")
        
        print("\n✅ Database migration completed successfully!")
        
        # Show summary
        print("\n📊 Database Summary:")
        print(f"  - Subscribers: {db.session.execute(text('SELECT COUNT(*) FROM subscribers')).scalar()}")
        print(f"  - Plans: {SubscriptionPlan.query.count()}")
        print(f"  - Discount Codes: {DiscountCode.query.count()}")
        print(f"  - Service Groups: {ServiceGroup.query.count()}")

if __name__ == '__main__':
    migrate_database()

