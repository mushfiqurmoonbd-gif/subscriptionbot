from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal

db = SQLAlchemy()

class Subscriber(db.Model):
    """Subscriber information model"""
    __tablename__ = 'subscribers'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    carrier = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255))
    name = db.Column(db.String(255))
    sms_email = db.Column(db.String(255), nullable=False)  # Generated email-to-SMS address
    
    # Telegram info
    telegram_user_id = db.Column(db.String(100))  # Telegram user ID
    telegram_username = db.Column(db.String(255))  # Telegram username
    
    # Timezone info
    timezone_offset_minutes = db.Column(db.Integer, default=0)  # Minutes offset from UTC
    timezone_label = db.Column(db.String(50), default='UTC')
    
    # Message delivery preferences
    # 'on_demand': User requests messages when they want
    # 'scheduled': Admin sends messages at scheduled times (not timezone-matched)
    # 'scheduled_timezone': Admin sends messages at scheduled times matched to user's timezone
    message_delivery_preference = db.Column(db.String(50), default='scheduled')  # on_demand, scheduled, scheduled_timezone
    use_timezone_matching = db.Column(db.Boolean, default=False)  # Whether to match scheduled times to user's timezone
    
    # Group/Service association
    group_id = db.Column(db.Integer, db.ForeignKey('service_groups.id'), nullable=True)
    
    # Subscription info
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'))
    payment_method = db.Column(db.String(50), default='stripe')  # stripe, paypal, crypto
    stripe_customer_id = db.Column(db.String(255))
    stripe_subscription_id = db.Column(db.String(255))
    paypal_subscription_id = db.Column(db.String(255))
    paypal_billing_agreement_id = db.Column(db.String(255))
    crypto_payment_address = db.Column(db.String(255))
    crypto_transaction_hash = db.Column(db.String(255))
    subscription_status = db.Column(db.String(50), default='inactive')  # active, inactive, canceled, past_due, pending
    
    # Discount and trial info
    discount_code_id = db.Column(db.Integer, db.ForeignKey('discount_codes.id'))
    applied_discount_percent = db.Column(db.Numeric(5, 2))  # Percentage discount applied
    final_price = db.Column(db.Numeric(10, 2))  # Final price after discount
    is_trial = db.Column(db.Boolean, default=False)
    trial_start_date = db.Column(db.DateTime)
    trial_end_date = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('ScheduledMessage', backref='subscriber', lazy=True, cascade='all, delete-orphan')
    plan = db.relationship('SubscriptionPlan', backref='subscribers', lazy=True)
    discount_code = db.relationship('DiscountCode', backref='subscribers', lazy=True)
    group = db.relationship('ServiceGroup', backref='subscribers', lazy=True)
    
    def __repr__(self):
        return f'<Subscriber {self.phone_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'carrier': self.carrier,
            'email': self.email,
            'name': self.name,
            'sms_email': self.sms_email,
            'payment_method': self.payment_method,
            'subscription_status': self.subscription_status,
            'timezone_offset_minutes': self.timezone_offset_minutes,
            'timezone_label': self.timezone_label,
            'message_delivery_preference': self.message_delivery_preference,
            'use_timezone_matching': self.use_timezone_matching,
            'group_id': self.group_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

class ScheduledMessage(db.Model):
    """Scheduled messages for subscribers"""
    __tablename__ = 'scheduled_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscribers.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    timezone_offset_minutes = db.Column(db.Integer, default=0)
    timezone_label = db.Column(db.String(50), default='UTC')
    
    def __repr__(self):
        return f'<ScheduledMessage {self.id} for subscriber {self.subscriber_id}>'

class Subscription(db.Model):
    """Subscription payment records"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscribers.id'), nullable=False)
    payment_method = db.Column(db.String(50), default='stripe')  # stripe, paypal, crypto
    
    # Stripe fields
    stripe_subscription_id = db.Column(db.String(255), unique=True)
    stripe_customer_id = db.Column(db.String(255))
    
    # PayPal fields
    paypal_subscription_id = db.Column(db.String(255))
    paypal_billing_agreement_id = db.Column(db.String(255))
    
    # Crypto fields
    crypto_payment_id = db.Column(db.String(255))
    crypto_transaction_hash = db.Column(db.String(255))
    crypto_currency = db.Column(db.String(10))  # BTC, ETH, USDC, etc.
    
    status = db.Column(db.String(50))  # active, canceled, past_due, pending, etc.
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        payment_id = self.stripe_subscription_id or self.paypal_subscription_id or self.crypto_payment_id
        return f'<Subscription {payment_id}>'

class DepositApproval(db.Model):
    """Deposit approval requests for manual crypto payments"""
    __tablename__ = 'deposit_approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscribers.id'), nullable=False)
    
    # Payment details
    currency = db.Column(db.String(10), nullable=False)  # BTC, ETH, USDC, USDT
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    wallet_address = db.Column(db.String(255), nullable=False)
    transaction_hash = db.Column(db.String(255))
    
    # Approval status
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text)  # Admin notes/reason for rejection
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.String(255))  # Admin identifier (optional)
    
    # Relationships
    subscriber = db.relationship('Subscriber', backref='deposit_approvals', lazy=True)
    
    def __repr__(self):
        return f'<DepositApproval {self.id} - {self.status}>'
    
    def to_dict(self):
        subscriber = self.subscriber
        return {
            'id': self.id,
            'subscriber_id': self.subscriber_id,
            'subscriber_name': subscriber.name if subscriber else None,
            'subscriber_phone': subscriber.phone_number if subscriber else None,
            'currency': self.currency,
            'amount': float(self.amount) if self.amount else None,
            'wallet_address': self.wallet_address,
            'transaction_hash': self.transaction_hash,
            'status': self.status,
            'admin_notes': self.admin_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by
        }

class SubscriptionPlan(db.Model):
    """Subscription pricing plans"""
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., "Basic", "Premium", "Pro"
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Monthly price in USD
    currency = db.Column(db.String(10), default='USD')
    
    # Trial settings
    has_trial = db.Column(db.Boolean, default=False)
    trial_days = db.Column(db.Integer, default=0)  # Number of days for free trial
    
    # Plan status
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)  # For ordering plans
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name} - ${self.price}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price) if self.price else None,
            'currency': self.currency,
            'has_trial': self.has_trial,
            'trial_days': self.trial_days,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def calculate_price_with_discount(self, discount_percent=None):
        """Calculate final price after discount."""
        base_price = float(self.price) if self.price else 0
        if discount_percent:
            discount_amount = base_price * (float(discount_percent) / 100)
            return round(base_price - discount_amount, 2)
        return base_price

class DiscountCode(db.Model):
    """Discount/promo codes for subscriptions"""
    __tablename__ = 'discount_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)  # Promo code (e.g., "SAVE50", "FREETRIAL")
    description = db.Column(db.Text)
    
    # Discount type
    discount_type = db.Column(db.String(20), default='percent')  # 'percent' or 'fixed'
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)  # Percentage (0-100) or fixed amount
    
    # Usage limits
    max_uses = db.Column(db.Integer, default=None)  # None = unlimited
    current_uses = db.Column(db.Integer, default=0)
    
    # Validity period
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, default=None)  # None = no expiration
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Plan restrictions (optional - None means applies to all plans)
    applicable_plan_ids = db.Column(db.String(255))  # Comma-separated plan IDs, None = all plans
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DiscountCode {self.code} - {self.discount_value}%>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'discount_type': self.discount_type,
            'discount_value': float(self.discount_value) if self.discount_value else None,
            'max_uses': self.max_uses,
            'current_uses': self.current_uses,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'is_active': self.is_active,
            'applicable_plan_ids': self.applicable_plan_ids,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_valid(self, plan_id=None):
        """Check if discount code is valid."""
        if not self.is_active:
            return False, "Discount code is not active"
        
        if self.max_uses and self.current_uses >= self.max_uses:
            return False, "Discount code has reached maximum uses"
        
        now = datetime.utcnow()
        if self.valid_from and now < self.valid_from:
            return False, "Discount code is not yet valid"
        
        if self.valid_until and now > self.valid_until:
            return False, "Discount code has expired"
        
        if self.applicable_plan_ids and plan_id:
            applicable_ids = [int(x.strip()) for x in self.applicable_plan_ids.split(',') if x.strip()]
            if plan_id not in applicable_ids:
                return False, "Discount code is not applicable to this plan"
        
        return True, "Valid"
    
    def apply_discount(self, base_price):
        """Apply discount to a price and return discounted price and discount amount."""
        base_price = float(base_price)
        
        if self.discount_type == 'percent':
            discount_amount = base_price * (float(self.discount_value) / 100)
            final_price = base_price - discount_amount
        else:  # fixed
            discount_amount = float(self.discount_value)
            final_price = max(0, base_price - discount_amount)  # Can't go below 0
        
        return round(final_price, 2), round(discount_amount, 2)

class ServiceGroup(db.Model):
    """Service groups for managing multiple groups/services on the same website"""
    __tablename__ = 'service_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., "Motivational Group", "Fitness Group"
    description = db.Column(db.Text)
    
    # Telegram bot start message (customizable per group)
    start_message = db.Column(db.Text, nullable=False)
    
    # Support contact info
    support_telegram_username = db.Column(db.String(255))  # e.g., "@admin" or "admin"
    support_email = db.Column(db.String(255))  # Support email address
    
    # Group settings
    is_active = db.Column(db.Boolean, default=True)
    default_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=True)
    
    # Scheduled message times (for motivational groups: morning, noon, evening)
    # Stored as JSON: {"morning": "08:00", "noon": "12:00", "evening": "18:00"}
    scheduled_times = db.Column(db.Text)  # JSON string with scheduled times
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    default_plan = db.relationship('SubscriptionPlan', backref='service_groups', lazy=True)
    
    def __repr__(self):
        return f'<ServiceGroup {self.name}>'
    
    def to_dict(self):
        import json
        scheduled_times = {}
        if self.scheduled_times:
            try:
                scheduled_times = json.loads(self.scheduled_times)
            except:
                scheduled_times = {}
        
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'start_message': self.start_message,
            'support_telegram_username': self.support_telegram_username,
            'support_email': self.support_email,
            'is_active': self.is_active,
            'default_plan_id': self.default_plan_id,
            'scheduled_times': scheduled_times,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

