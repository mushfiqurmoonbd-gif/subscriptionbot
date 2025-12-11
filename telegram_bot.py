"""
Telegram Bot for Subscription Service
Handles user interactions through Telegram to collect subscriber information
and manage subscriptions.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
from config import Config
from models import db, Subscriber, SubscriptionPlan, DiscountCode, DepositApproval, ServiceGroup
from plan_manager import get_active_plans, get_plan_by_id, validate_discount_code, apply_discount_code, increment_discount_code_usage
from email_sms_gateways import get_sms_email, list_available_carriers, EMAIL_SMS_GATEWAYS
from subscription_manager import create_subscription as create_stripe_subscription
from paypal_manager import create_paypal_subscription
from crypto_manager import create_crypto_checkout, create_manual_crypto_subscription, get_crypto_wallet_addresses, get_available_crypto_currencies
from sms_sender import send_sms_to_subscriber
from scheduler import schedule_message
from datetime import datetime
import logging
import asyncio
import stripe

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Helper function to escape Markdown special characters
def escape_markdown(text):
    """Escape special Markdown characters."""
    if not text:
        return text
    # Characters that need escaping in Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = str(text).replace(char, f'\\{char}')
    return text

# Initialize Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

# Conversation states
PHONE_NUMBER, CARRIER, EMAIL, NAME, TIMEZONE_SELECTION, DELIVERY_PREFERENCE, PLAN_SELECTION, DISCOUNT_CODE, PAYMENT_METHOD, CRYPTO_CURRENCY = range(10)

# Store user data during conversation
user_data_store = {}

def get_payment_method_keyboard():
    """Get inline keyboard for payment method selection."""
    keyboard = [
        [
            InlineKeyboardButton("💳 Stripe (Card)", callback_data="payment_stripe"),
            InlineKeyboardButton("🅿️ PayPal", callback_data="payment_paypal"),
        ],
        [
            InlineKeyboardButton("₿ Crypto (Coinbase)", callback_data="payment_crypto_coinbase"),
            InlineKeyboardButton("₿ Crypto (Manual)", callback_data="payment_crypto_manual"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_carrier_keyboard():
    """Get inline keyboard for carrier selection."""
    carriers = list_available_carriers()
    keyboard = []
    row = []
    for i, carrier in enumerate(carriers[:12]):  # Limit to 12 carriers
        row.append(InlineKeyboardButton(carrier.capitalize(), callback_data=f"carrier_{carrier}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def get_crypto_currency_keyboard():
    """Get inline keyboard for cryptocurrency selection."""
    # Get available currencies that have wallet addresses configured
    available_currencies = get_available_crypto_currencies()
    
    # Currency display names and emojis
    currency_display = {
        'BTC': ('₿ Bitcoin (BTC)', 'BTC'),
        'ETH': ('Ξ Ethereum (ETH)', 'ETH'),
        'USDC': ('💵 USDC', 'USDC'),
        'USDT': ('💵 USDT', 'USDT'),
    }
    
    keyboard = []
    row = []
    
    # Add Coinbase Commerce option first (always available if API key is set)
    if Config.COINBASE_COMMERCE_API_KEY:
        keyboard.append([
            InlineKeyboardButton("🛒 Coinbase Commerce (Auto)", callback_data="crypto_coinbase")
        ])
    
    # Add manual wallet options for configured currencies
    for currency in ['BTC', 'ETH', 'USDC', 'USDT']:
        if currency in available_currencies:
            display_name, _ = currency_display.get(currency, (currency, currency))
            row.append(InlineKeyboardButton(display_name, callback_data=f"crypto_{currency}"))
            
            # Add row when we have 2 buttons
            if len(row) == 2:
                keyboard.append(row)
                row = []
    
    # Add remaining button if any
    if row:
        keyboard.append(row)
    
    # If no options available, return None (shouldn't happen if crypto payment is selected)
    if not keyboard:
        return None
    
    return InlineKeyboardMarkup(keyboard)

def get_plan_keyboard():
    """Get inline keyboard for plan selection."""
    from app import app
    with app.app_context():
        plans = get_active_plans()
        
        if not plans:
            return None
        
        keyboard = []
        for plan in plans:
            trial_text = f" ({plan.trial_days} days free trial)" if plan.has_trial else ""
            button_text = f"{plan.name} - ${format_price(plan.price)}/month{trial_text}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"plan_{plan.id}")])
        
        return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for phone number."""
    user = update.effective_user
    
    # Check if user already has a conversation
    if user.id in user_data_store:
        # Clear previous data
        del user_data_store[user.id]
    
    # Check if user already has a subscription
    from app import app
    with app.app_context():
        existing_subscriber = Subscriber.query.filter_by(
            telegram_user_id=str(user.id)
        ).first()
        
        if existing_subscriber:
            status = existing_subscriber.subscription_status
            status_emoji = {
                'active': '✅',
                'pending': '⏳',
                'inactive': '❌',
                'cancelled': '🚫'
            }.get(status, '❓')
            
            status_text = {
                'active': 'Active',
                'pending': 'Pending Approval',
                'inactive': 'Inactive',
                'cancelled': 'Cancelled'
            }.get(status, status.capitalize())
            
            phone_escaped = escape_markdown(existing_subscriber.phone_number)
            carrier_escaped = escape_markdown(existing_subscriber.carrier.capitalize()) if existing_subscriber.carrier else 'N/A'
            payment_escaped = escape_markdown(existing_subscriber.payment_method.capitalize()) if existing_subscriber.payment_method else 'N/A'
            timezone_display = escape_markdown(
                format_timezone_display(existing_subscriber.timezone_label, existing_subscriber.timezone_offset_minutes)
            )
            
            message = (
                f"{status_emoji} **You already have a subscription!**\n\n"
                f"📱 Phone: {phone_escaped}\n"
                f"📡 Carrier: {carrier_escaped}\n"
                f"💳 Payment: {payment_escaped}\n"
                f"🕒 Timezone: {timezone_display}\n"
                f"📊 Status: {status_text}\n\n"
            )
            
            if status == 'active':
                message += "✅ Your subscription is active. You will receive SMS messages as scheduled."
            elif status == 'pending':
                message += "⏳ Your subscription is pending approval. Please wait for admin confirmation."
            elif status == 'inactive':
                message += "❌ Your subscription is inactive. Please contact support if you need assistance."
            elif status == 'cancelled':
                message += "🚫 Your subscription has been cancelled. Please contact support to reactivate."
            else:
                message += "Please contact support for more information."
            
            try:
                await update.message.reply_text(message, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(
                    f"{status_emoji} You already have a subscription!\n\n"
                    f"Phone: {existing_subscriber.phone_number}\n"
                    f"Carrier: {existing_subscriber.carrier.capitalize() if existing_subscriber.carrier else 'N/A'}\n"
                    f"Payment: {existing_subscriber.payment_method.capitalize() if existing_subscriber.payment_method else 'N/A'}\n"
                    f"Timezone: {format_timezone_display(existing_subscriber.timezone_label, existing_subscriber.timezone_offset_minutes)}\n"
                    f"Status: {status_text}\n\n"
                    + ("✅ Your subscription is active." if status == 'active' else
                       "⏳ Your subscription is pending approval." if status == 'pending' else
                       "❌ Your subscription is inactive." if status == 'inactive' else
                       "🚫 Your subscription has been cancelled.")
                )
            
            return ConversationHandler.END
    
    # Get group-based start message
    group_id = Config.DEFAULT_GROUP_ID
    welcome_message = Config.DEFAULT_START_MESSAGE
    
    if group_id:
        try:
            group = ServiceGroup.query.filter_by(id=group_id, is_active=True).first()
            if group and group.start_message:
                welcome_message = group.start_message
        except Exception as e:
            logger.warning(f"Could not load group {group_id}: {e}")
    
    try:
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")
        # Try without markdown
        await update.message.reply_text(
            welcome_message.replace('**', '').replace('*', '')
        )
    
    # Initialize user data
    user_data_store[user.id] = {
        'telegram_user_id': str(user.id),
        'telegram_username': user.username,
        'timezone_offset_minutes': 0,
        'timezone_label': 'UTC',
        'group_id': int(group_id) if group_id else None,
        'message_delivery_preference': 'scheduled',
        'use_timezone_matching': False
    }
    
    return PHONE_NUMBER

async def phone_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input."""
    user = update.effective_user
    phone_text = update.message.text.strip()
    
    # Clean phone number (remove non-digits)
    phone_number = ''.join(filter(str.isdigit, phone_text))
    
    if len(phone_number) != 10:
        await update.message.reply_text(
            "❌ Please enter a valid 10-digit phone number (e.g., 1234567890)"
        )
        return PHONE_NUMBER
    
    # Check if subscriber already exists
    from app import app
    with app.app_context():
        existing = Subscriber.query.filter_by(phone_number=phone_number).first()
    if existing:
        await update.message.reply_text(
            f"⚠️ This phone number is already registered.\n\n"
            f"Status: {existing.subscription_status}\n"
            f"Payment Method: {existing.payment_method}\n\n"
            "Use /cancel to start over or /status to check your subscription."
        )
        return ConversationHandler.END
    
    # Store phone number
    user_data_store[user.id]['phone_number'] = phone_number
    
    # Ask for carrier
    carrier_list = "\n".join([f"• {c.capitalize()}" for c in list_available_carriers()[:10]])
    
    await update.message.reply_text(
        f"✅ Phone number received: {phone_number}\n\n"
        f"📱 **Step 2:** Select your carrier:",
        reply_markup=get_carrier_keyboard(),
        parse_mode='Markdown'
    )
    
    return CARRIER

async def carrier_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle carrier selection."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    carrier = query.data.replace("carrier_", "")
    
    user_data_store[user.id]['carrier'] = carrier
    
    await query.edit_message_text(
        f"✅ Carrier selected: {carrier.capitalize()}\n\n"
        f"📧 **Step 3:** Send your email address (or /skip to skip)",
        parse_mode='Markdown'
    )
    
    return EMAIL

async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email input."""
    user = update.effective_user
    email = update.message.text.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        await update.message.reply_text(
            "❌ Please enter a valid email address (or /skip to skip)"
        )
        return EMAIL
    
    user_data_store[user.id]['email'] = email
    
    await update.message.reply_text(
        f"✅ Email received: {email}\n\n"
        f"👤 **Step 4:** Send your name (or /skip to skip)",
        parse_mode='Markdown'
    )
    
    return NAME

async def skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip email input."""
    user = update.effective_user
    user_data_store[user.id]['email'] = None
    
    await update.message.reply_text(
        "⏭️ Email skipped.\n\n"
        "👤 **Step 4:** Send your name (or /skip to skip)",
        parse_mode='Markdown'
    )
    
    return NAME

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input."""
    user = update.effective_user
    name = update.message.text.strip()
    
    user_data_store[user.id]['name'] = name
    
    timezone_keyboard = get_timezone_keyboard()
    if not timezone_keyboard:
        await update.message.reply_text(
            "❌ Unable to load timezone options. Please contact support."
        )
        return ConversationHandler.END
    
    name_escaped = escape_markdown(name)
    await update.message.reply_text(
        f"✅ Name received: {name_escaped}\n\n"
        f"🌍 **Step 5:** Choose your timezone so we can send messages at the right local time:",
        reply_markup=timezone_keyboard,
        parse_mode='Markdown'
    )
    
    return TIMEZONE_SELECTION

async def skip_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip name input."""
    user = update.effective_user
    user_data_store[user.id]['name'] = None
    
    timezone_keyboard = get_timezone_keyboard()
    if not timezone_keyboard:
        await update.message.reply_text(
            "❌ Unable to load timezone options. Please contact support."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "⏭️ Name skipped.\n\n"
        "🌍 **Step 5:** Choose your timezone so we can send messages at the right local time:",
        reply_markup=timezone_keyboard,
        parse_mode='Markdown'
    )
    
    return TIMEZONE_SELECTION

async def timezone_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timezone selection."""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data.replace("tz_", "")
    
    try:
        offset_minutes = int(data)
    except ValueError:
        offset_minutes = 0
    
    label = TIMEZONE_LOOKUP.get(offset_minutes, None)
    if not label:
        # Derive label if not in lookup
        sign = '+' if offset_minutes >= 0 else '-'
        minutes_abs = abs(offset_minutes)
        hours = minutes_abs // 60
        mins = minutes_abs % 60
        label = f"UTC{sign}{hours:02d}:{mins:02d}"
    
    user_data = user_data_store.setdefault(user.id, {})
    user_data['timezone_offset_minutes'] = offset_minutes
    user_data['timezone_label'] = label
    
    plan_keyboard = get_plan_keyboard()
    if not plan_keyboard:
        await query.edit_message_text(
            "❌ No subscription plans available. Please contact support."
        )
        return ConversationHandler.END
    
    timezone_display = format_timezone_display(label, offset_minutes)
    timezone_display_escaped = escape_markdown(timezone_display)
    
    # Show delivery preference selection
    delivery_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📨 On-Demand (Request when you want)", callback_data="delivery_on_demand")
        ],
        [
            InlineKeyboardButton("⏰ Scheduled (Admin sends at set times)", callback_data="delivery_scheduled")
        ],
        [
            InlineKeyboardButton("🌍 Scheduled + Timezone Match", callback_data="delivery_scheduled_tz")
        ]
    ])
    
    await query.edit_message_text(
        f"🌍 Timezone selected: {timezone_display_escaped}\n\n"
        f"📬 **Step 6:** How would you like to receive messages?\n\n"
        f"• **On-Demand**: Request messages when you want\n"
        f"• **Scheduled**: Admin sends at scheduled times\n"
        f"• **Scheduled + Timezone**: Messages matched to your timezone (e.g., morning at 8 AM your time)",
        reply_markup=delivery_keyboard,
        parse_mode='Markdown'
    )
    
    return DELIVERY_PREFERENCE

async def skip_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip timezone selection (defaults to UTC)."""
    user = update.effective_user
    user_data = user_data_store.setdefault(user.id, {})
    user_data['timezone_offset_minutes'] = 0
    user_data['timezone_label'] = 'UTC'
    
    # Show delivery preference selection
    delivery_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📨 On-Demand (Request when you want)", callback_data="delivery_on_demand")
        ],
        [
            InlineKeyboardButton("⏰ Scheduled (Admin sends at set times)", callback_data="delivery_scheduled")
        ],
        [
            InlineKeyboardButton("🌍 Scheduled + Timezone Match", callback_data="delivery_scheduled_tz")
        ]
    ])
    
    await update.message.reply_text(
        "⏭️ Timezone skipped. Using UTC as default.\n\n"
        "📬 **Step 6:** How would you like to receive messages?\n\n"
        "• **On-Demand**: Request messages when you want\n"
        "• **Scheduled**: Admin sends at scheduled times\n"
        "• **Scheduled + Timezone**: Messages matched to your timezone (e.g., morning at 8 AM your time)",
        reply_markup=delivery_keyboard,
        parse_mode='Markdown'
    )
    
    return DELIVERY_PREFERENCE

async def delivery_preference_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle delivery preference selection."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data.replace("delivery_", "")
    
    user_data = user_data_store.setdefault(user.id, {})
    
    if data == "on_demand":
        user_data['message_delivery_preference'] = 'on_demand'
        user_data['use_timezone_matching'] = False
        preference_text = "📨 On-Demand"
    elif data == "scheduled_tz":
        user_data['message_delivery_preference'] = 'scheduled_timezone'
        user_data['use_timezone_matching'] = True
        preference_text = "🌍 Scheduled + Timezone Match"
    else:  # scheduled
        user_data['message_delivery_preference'] = 'scheduled'
        user_data['use_timezone_matching'] = False
        preference_text = "⏰ Scheduled"
    
    plan_keyboard = get_plan_keyboard()
    if not plan_keyboard:
        await query.edit_message_text(
            "❌ No subscription plans available. Please contact support."
        )
        return ConversationHandler.END
    
    preference_text_escaped = escape_markdown(preference_text)
    
    await query.edit_message_text(
        f"✅ Delivery preference: {preference_text_escaped}\n\n"
        f"📦 **Step 7:** Select your subscription plan:",
        reply_markup=plan_keyboard,
        parse_mode='Markdown'
    )
    
    return PLAN_SELECTION

async def plan_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle plan selection."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    plan_id = int(query.data.replace("plan_", ""))
    
    from app import app
    with app.app_context():
        plan = get_plan_by_id(plan_id)
        if not plan or not plan.is_active:
            await query.edit_message_text(
                "❌ Selected plan is not available. Please try again with /start"
            )
            return ConversationHandler.END
        
        user_data_store[user.id]['plan_id'] = plan_id
        user_data_store[user.id]['plan'] = plan
        
        trial_text = f"\n🎁 **Free Trial:** {plan.trial_days} days" if plan.has_trial else ""
        plan_name_escaped = escape_markdown(plan.name)
        price_escaped = escape_markdown(f"${format_price(plan.price)}")
        
        message = (
            f"✅ Plan selected: **{plan_name_escaped}**\n\n"
            f"💰 Price: {price_escaped}/month{trial_text}\n\n"
            f"💳 **Step 7:** Do you have a discount code?\n"
            f"Send your code or type /skip to continue without a code."
        )
        
        try:
            await query.edit_message_text(message, parse_mode='Markdown')
        except Exception:
            await query.edit_message_text(
                f"✅ Plan selected: {plan.name}\n\n"
                f"Price: {price_escaped}/month{trial_text}\n\n"
                f"💳 Step 7: Do you have a discount code?\n"
                f"Send your code or type /skip to continue without a code."
            )
    
    return DISCOUNT_CODE

async def discount_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle discount code input."""
    user = update.effective_user
    code_text = update.message.text.strip().upper()
    
    from app import app
    with app.app_context():
        plan_id = user_data_store[user.id].get('plan_id')
        is_valid, discount_code, error_msg = validate_discount_code(code_text, plan_id)
        
        if not is_valid:
            await update.message.reply_text(
                f"❌ **Invalid Discount Code**\n\n{error_msg}\n\n"
                f"Please try again or type /skip to continue without a code.",
                parse_mode='Markdown'
            )
            return DISCOUNT_CODE
        
        # Apply discount
        plan = user_data_store[user.id]['plan']
        pricing = apply_discount_code(discount_code, plan)
        
        user_data_store[user.id]['discount_code'] = discount_code.code
        user_data_store[user.id]['discount_code_id'] = discount_code.id
        user_data_store[user.id]['final_price'] = pricing['final_price']
        user_data_store[user.id]['discount_percent'] = pricing['discount_percent']
        
        discount_text = ""
        if pricing['discount_percent']:
            discount_text = f"{pricing['discount_percent']:.0f}% off"
        else:
            discount_text = f"${pricing['discount_amount']:.2f} off"
        
        base_price_escaped = escape_markdown(f"${pricing['base_price']:.2f}")
        final_price_escaped = escape_markdown(f"${pricing['final_price']:.2f}")
        discount_text_escaped = escape_markdown(discount_text)
        code_escaped = escape_markdown(discount_code.code)
        
        if pricing['is_free']:
            message = (
                f"🎉 **Discount Applied!**\n\n"
                f"Code: `{code_escaped}`\n"
                f"Discount: {discount_text_escaped}\n"
                f"Original Price: {base_price_escaped}\n"
                f"**Final Price: FREE!** 🎁\n\n"
                f"💳 **Step 8:** Select your payment method:"
            )
        else:
            message = (
                f"✅ **Discount Applied!**\n\n"
                f"Code: `{code_escaped}`\n"
                f"Discount: {discount_text_escaped}\n"
                f"Original Price: {base_price_escaped}\n"
                f"**Final Price: {final_price_escaped}**\n\n"
                f"💳 **Step 8:** Select your payment method:"
            )
        
        try:
            await update.message.reply_text(
                message,
                reply_markup=get_payment_method_keyboard(),
                parse_mode='Markdown'
            )
        except Exception:
            await update.message.reply_text(
                f"✅ Discount Applied!\n\n"
                f"Code: {discount_code.code}\n"
                f"Discount: {discount_text}\n"
                f"Original Price: ${pricing['base_price']:.2f}\n"
                f"Final Price: ${pricing['final_price']:.2f}\n\n"
                f"💳 Step 8: Select your payment method:",
                reply_markup=get_payment_method_keyboard()
            )
    
    return PAYMENT_METHOD

async def skip_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip discount code input."""
    user = update.effective_user
    user_data_store[user.id]['discount_code'] = None
    user_data_store[user.id]['discount_code_id'] = None
    
    plan = user_data_store[user.id]['plan']
    plan_name_escaped = escape_markdown(plan.name)
    price_escaped = escape_markdown(f"${format_price(plan.price)}")
    
    message = (
        f"⏭️ No discount code.\n\n"
        f"Plan: **{plan_name_escaped}**\n"
        f"Price: {price_escaped}/month\n\n"
        f"💳 **Step 8:** Select your payment method:"
    )
    
    try:
        await update.message.reply_text(
            message,
            reply_markup=get_payment_method_keyboard(),
            parse_mode='Markdown'
        )
    except Exception:
        await update.message.reply_text(
            f"⏭️ No discount code.\n\n"
            f"Plan: {plan.name}\n"
            f"Price: {price_escaped}\n\n"
            f"💳 Step 8: Select your payment method:",
            reply_markup=get_payment_method_keyboard()
        )
    
    return PAYMENT_METHOD

async def payment_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Handle plan selection callback
    if data.startswith("plan_"):
        return await plan_selection_callback(update, context)
    
    if data.startswith("payment_"):
        payment_type = data.replace("payment_", "")
        
        if payment_type == "stripe":
            await process_subscription(user.id, "stripe", query, update)
        elif payment_type == "paypal":
            await process_subscription(user.id, "paypal", query, update)
        elif payment_type == "crypto_coinbase":
            await process_subscription(user.id, "crypto", query, update, crypto_type="coinbase")
        elif payment_type == "crypto_manual":
            await query.edit_message_text(
                "₿ **Select cryptocurrency:**",
                reply_markup=get_crypto_currency_keyboard(),
                parse_mode='Markdown'
            )
            return CRYPTO_CURRENCY
    elif data.startswith("crypto_"):
        currency = data.replace("crypto_", "")
        await process_subscription(user.id, "crypto", query, update, crypto_type="manual", currency=currency)
    
    return ConversationHandler.END

async def process_subscription(user_id, payment_method, query, update, crypto_type=None, currency=None):
    """Process subscription creation."""
    try:
        user_data = user_data_store.get(user_id)
        if not user_data:
            await query.edit_message_text("❌ Error: Session expired. Please start over with /start")
            return
        
        # Check if user already has a subscription
        from app import app
        with app.app_context():
            existing_subscriber = Subscriber.query.filter_by(
                telegram_user_id=str(user_id)
            ).first()
            
            if existing_subscriber:
                status = existing_subscriber.subscription_status
                status_emoji = {
                    'active': '✅',
                    'pending': '⏳',
                    'inactive': '❌',
                    'cancelled': '🚫'
                }.get(status, '❓')
                
                status_text = {
                    'active': 'Active',
                    'pending': 'Pending Approval',
                    'inactive': 'Inactive',
                    'cancelled': 'Cancelled'
                }.get(status, status.capitalize())
                
                phone_escaped = escape_markdown(existing_subscriber.phone_number)
                message = (
                    f"❌ **You already have a subscription!**\n\n"
                    f"📱 Phone: {phone_escaped}\n"
                    f"📊 Status: {status_text}\n\n"
                    f"Only one subscription per Telegram account is allowed.\n"
                    f"Use /start to check your current subscription status."
                )
                
                try:
                    await query.edit_message_text(message, parse_mode='Markdown')
                except Exception:
                    await query.edit_message_text(
                        f"❌ You already have a subscription!\n\n"
                        f"Phone: {existing_subscriber.phone_number}\n"
                        f"Status: {status_text}\n\n"
                        f"Only one subscription per Telegram account is allowed.\n"
                        f"Use /start to check your current subscription status."
                    )
                return
        
        # Generate SMS email address
        sms_email = get_sms_email(user_data['phone_number'], user_data['carrier'])
        
        # Get plan and discount info
        plan = user_data.get('plan')
        plan_id = user_data.get('plan_id')
        discount_code_id = user_data.get('discount_code_id')
        final_price = user_data.get('final_price')
        discount_percent = user_data.get('discount_percent')
        
        if not plan:
            from plan_manager import get_default_plan
            plan = get_default_plan()
            if plan:
                plan_id = plan.id
                if final_price is None:
                    final_price = float(plan.price)
        
        # Create subscriber with database context
        with app.app_context():
            subscriber = Subscriber(
                phone_number=user_data['phone_number'],
                carrier=user_data['carrier'],
                email=user_data.get('email'),
                name=user_data.get('name'),
                sms_email=sms_email,
                telegram_user_id=user_data['telegram_user_id'],
                telegram_username=user_data.get('telegram_username'),
                payment_method=payment_method,
                subscription_status='inactive',
                plan_id=plan_id,
                discount_code_id=discount_code_id,
                applied_discount_percent=discount_percent,
                final_price=final_price,
                timezone_offset_minutes=user_data.get('timezone_offset_minutes', 0),
                timezone_label=user_data.get('timezone_label', 'UTC'),
                message_delivery_preference=user_data.get('message_delivery_preference', 'scheduled'),
                use_timezone_matching=user_data.get('use_timezone_matching', False),
                group_id=user_data.get('group_id')
            )
            
            # Handle trial period
            if plan and plan.has_trial:
                from datetime import timedelta
                subscriber.is_trial = True
                subscriber.trial_start_date = datetime.utcnow()
                subscriber.trial_end_date = datetime.utcnow() + timedelta(days=plan.trial_days)
            
            db.session.add(subscriber)
            db.session.commit()
            
            # Increment discount code usage if applicable
            if discount_code_id:
                discount_code = DiscountCode.query.get(discount_code_id)
                if discount_code:
                    increment_discount_code_usage(discount_code)
            
            # Get the subscriber ID for later use
            subscriber_id = subscriber.id
            
            # Create subscription based on payment method
            if payment_method == 'stripe':
                try:
                    # Create Stripe customer first (if not exists)
                    if not subscriber.stripe_customer_id:
                        from subscription_manager import create_stripe_customer
                        create_stripe_customer(subscriber)
                    
                    # Create Stripe Checkout session for payment collection
                    # This will automatically create the subscription when payment is collected
                    try:
                        checkout_session = stripe.checkout.Session.create(
                            customer=subscriber.stripe_customer_id,
                            payment_method_types=['card'],
                            line_items=[{
                                'price_data': {
                                    'currency': 'usd',
                                    'product_data': {'name': f'{plan.name if plan else "Monthly"} Subscription'},
                                    'unit_amount': int((final_price if final_price else (float(plan.price) if plan else Config.MONTHLY_PRICE)) * 100),
                                    'recurring': {'interval': 'month'}
                                },
                                'quantity': 1,
                            }],
                            mode='subscription',
                            success_url=f"{Config.BASE_URL}/api/subscribe/success?session_id={{CHECKOUT_SESSION_ID}}",
                            cancel_url=f"{Config.BASE_URL}/api/subscribe/cancel",
                            metadata={
                                'subscriber_id': subscriber.id,
                                'phone_number': subscriber.phone_number
                            }
                        )
                        payment_url = checkout_session.url
                        
                        # Update subscriber status to pending
                        subscriber.subscription_status = 'pending'
                        db.session.commit()
                        
                        phone_escaped = escape_markdown(subscriber.phone_number)
                        carrier_escaped = escape_markdown(subscriber.carrier.capitalize())
                        payment_url_escaped = payment_url.replace('_', '\\_').replace('*', '\\*')
                        message = (
                            f"✅ **Subscription Setup Started!**\n\n"
                            f"📱 Phone: {phone_escaped}\n"
                            f"📡 Carrier: {carrier_escaped}\n"
                            f"💳 Payment: Stripe\n\n"
                            f"🔗 **Complete Payment:**\n{payment_url_escaped}\n\n"
                            f"Click the link above to add your payment method and activate your subscription."
                        )
                        
                        try:
                            await query.edit_message_text(message, parse_mode='Markdown')
                        except Exception:
                            await query.edit_message_text(
                                f"✅ Subscription Setup Started!\n\n"
                                f"📱 Phone: {subscriber.phone_number}\n"
                                f"📡 Carrier: {subscriber.carrier.capitalize()}\n"
                                f"💳 Payment: Stripe\n\n"
                                f"🔗 Complete Payment:\n{payment_url}\n\n"
                                f"Click the link above to add your payment method and activate your subscription."
                            )
                    except Exception as e:
                        logger.error(f"Error creating checkout session: {e}")
                        error_msg = escape_markdown(str(e))
                        message = (
                            f"❌ **Payment Setup Error**\n\n"
                            f"Error: {error_msg}\n\n"
                            f"Please try again with /start or contact support."
                        )
                        try:
                            await query.edit_message_text(message, parse_mode='Markdown')
                        except Exception:
                            await query.edit_message_text(
                                f"❌ Payment Setup Error\n\nError: {str(e)}\n\nPlease try again with /start or contact support."
                            )
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error creating Stripe subscription: {e}")
                    
                    # Show user-friendly error message
                    error_msg_escaped = escape_markdown(error_msg)
                    message = (
                        f"❌ **Subscription Error**\n\n"
                        f"Error: {error_msg_escaped}\n\n"
                        f"Please try again with /start or contact support."
                    )
                    try:
                        await query.edit_message_text(message, parse_mode='Markdown')
                    except Exception:
                        await query.edit_message_text(
                            f"❌ Subscription Error\n\nError: {error_msg}\n\nPlease try again with /start or contact support."
                        )
            
            elif payment_method == 'paypal':
                subscription = create_paypal_subscription(subscriber, plan=plan, final_price=final_price)
                approval_url = subscription.get('approval_url', '')
                phone_escaped = escape_markdown(subscriber.phone_number)
                carrier_escaped = escape_markdown(subscriber.carrier.capitalize())
                message = (
                    f"✅ **Subscription Created!**\n\n"
                    f"📱 Phone: {phone_escaped}\n"
                    f"📡 Carrier: {carrier_escaped}\n"
                    f"🅿️ Payment: PayPal\n"
                    f"Status: Pending Approval\n\n"
                    f"🔗 Please approve your subscription:\n{approval_url}"
                )
                try:
                    await query.edit_message_text(message, parse_mode='Markdown')
                except Exception:
                    await query.edit_message_text(
                        f"✅ Subscription Created!\n\n"
                        f"📱 Phone: {subscriber.phone_number}\n"
                        f"📡 Carrier: {subscriber.carrier.capitalize()}\n"
                        f"🅿️ Payment: PayPal\n"
                        f"Status: Pending Approval\n\n"
                        f"🔗 Please approve your subscription:\n{approval_url}"
                    )
            
            elif payment_method == 'crypto':
                if crypto_type == 'coinbase':
                    checkout = create_crypto_checkout(subscriber, plan=plan, final_price=final_price)
                    checkout_url = checkout.get('hosted_url', '')
                    phone_escaped = escape_markdown(subscriber.phone_number)
                    carrier_escaped = escape_markdown(subscriber.carrier.capitalize())
                    message = (
                        f"✅ **Subscription Created!**\n\n"
                        f"📱 Phone: {phone_escaped}\n"
                        f"📡 Carrier: {carrier_escaped}\n"
                        f"₿ Payment: Cryptocurrency (Coinbase)\n"
                        f"Status: Pending Payment\n\n"
                        f"🔗 Complete payment:\n{checkout_url}"
                    )
                    try:
                        await query.edit_message_text(message, parse_mode='Markdown')
                    except Exception:
                        await query.edit_message_text(
                            f"✅ Subscription Created!\n\n"
                            f"📱 Phone: {subscriber.phone_number}\n"
                            f"📡 Carrier: {subscriber.carrier.capitalize()}\n"
                            f"₿ Payment: Cryptocurrency (Coinbase)\n"
                            f"Status: Pending Payment\n\n"
                            f"🔗 Complete payment:\n{checkout_url}"
                        )
                else:
                    try:
                        payment_info = create_manual_crypto_subscription(subscriber, currency=currency, plan=plan, final_price=final_price)
                        wallet_addr = payment_info['wallet_address']
                        amount = payment_info['amount']
                        # Escape wallet address for Markdown
                        wallet_addr_escaped = wallet_addr.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
                        phone_escaped = escape_markdown(subscriber.phone_number)
                        carrier_escaped = escape_markdown(subscriber.carrier.capitalize())
                        amount_escaped = escape_markdown(f"${amount:.2f}")
                        message = (
                            f"✅ **Subscription Created!**\n\n"
                            f"📱 Phone: {phone_escaped}\n"
                            f"📡 Carrier: {carrier_escaped}\n"
                            f"₿ Payment: {currency}\n"
                            f"Status: Pending Payment\n\n"
                            f"💰 Send {amount_escaped} worth of {currency} to:\n"
                            f"`{wallet_addr_escaped}`\n\n"
                            f"After payment, use /verify_payment with your transaction hash."
                        )
                    except ValueError as e:
                        # Handle wallet address not configured error
                        error_msg = str(e)
                        # Escape error message for Markdown
                        error_msg_escaped = escape_markdown(error_msg)
                        available_currencies = get_available_crypto_currencies()
                        coinbase_available = Config.COINBASE_COMMERCE_API_KEY is not None
                        
                        suggestion = ""
                        if coinbase_available:
                            suggestion = "\n\n💡 **Tip:** Use Coinbase Commerce for automatic crypto payments (no wallet setup needed)."
                        elif available_currencies:
                            currencies_str = ', '.join(available_currencies)
                            suggestion = f"\n\n💡 **Available currencies:** {currencies_str}"
                        
                        message = (
                            f"❌ **Wallet Not Configured**\n\n"
                            f"{error_msg_escaped}{suggestion}\n\n"
                            f"Please contact admin or try a different payment method."
                        )
                        logger.error(f"Error creating crypto subscription: {e}")
                    try:
                        await query.edit_message_text(message, parse_mode='Markdown')
                    except Exception:
                        # Fallback to plain text if Markdown parsing fails
                        plain_message = message.replace('**', '').replace('`', '')
                        await query.edit_message_text(plain_message)
        
        # Clean up user data
        del user_data_store[user_id]
        
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        error_msg = escape_markdown(str(e))
        try:
            await query.edit_message_text(
                f"❌ Error creating subscription: {error_msg}\n\n"
                "Please try again with /start",
                parse_mode='Markdown'
            )
        except Exception:
            # If Markdown parsing fails, send without parse_mode
            await query.edit_message_text(
                f"❌ Error creating subscription: {str(e)}\n\n"
                "Please try again with /start"
            )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    user = update.effective_user
    if user.id in user_data_store:
        del user_data_store[user.id]
    
    await update.message.reply_text(
        "❌ Subscription process cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check subscription status."""
    user = update.effective_user
    from app import app
    with app.app_context():
        subscriber = Subscriber.query.filter_by(telegram_user_id=str(user.id)).first()
        
        if not subscriber:
            await update.message.reply_text(
                "❌ No subscription found. Use /start to subscribe."
            )
            return
        
        message = (
            f"📊 **Your Subscription Status**\n\n"
            f"📱 Phone: {subscriber.phone_number}\n"
            f"📡 Carrier: {subscriber.carrier.capitalize()}\n"
            f"💳 Payment Method: {subscriber.payment_method.capitalize()}\n"
            f"✅ Status: {subscriber.subscription_status}\n"
            f"📅 Created: {subscriber.created_at.strftime('%Y-%m-%d %H:%M') if subscriber.created_at else 'N/A'}\n"
        )

        timezone_display = escape_markdown(
            format_timezone_display(subscriber.timezone_label, subscriber.timezone_offset_minutes)
        )
        message += f"🕒 Timezone: {timezone_display}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify crypto payment with transaction hash."""
    user = update.effective_user
    
    # Get transaction hash from command arguments
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ **Invalid Command**\n\n"
            "Please provide your transaction hash:\n"
            "`/verify_payment YOUR_TRANSACTION_HASH`\n\n"
            "Example: `/verify_payment abc123def456...`",
            parse_mode='Markdown'
        )
        return
    
    transaction_hash = ' '.join(context.args).strip()
    
    if not transaction_hash or len(transaction_hash) < 10:
        await update.message.reply_text(
            "❌ **Invalid Transaction Hash**\n\n"
            "Transaction hash must be at least 10 characters long.\n"
            "Please check and try again."
        )
        return
    
    from app import app
    from models import DepositApproval
    
    with app.app_context():
        # Find subscriber by Telegram user ID
        subscriber = Subscriber.query.filter_by(telegram_user_id=str(user.id)).first()
        
        if not subscriber:
            await update.message.reply_text(
                "❌ **No Subscription Found**\n\n"
                "You don't have an active subscription.\n"
                "Use /start to create a new subscription."
            )
            return
        
        # Check if payment method is crypto
        if subscriber.payment_method != 'crypto':
            await update.message.reply_text(
                "❌ **Invalid Payment Method**\n\n"
                f"Your payment method is {subscriber.payment_method.capitalize()}, not crypto.\n"
                "This command is only for crypto payments."
            )
            return
        
        # Find pending deposit approval for this subscriber
        deposit_approval = DepositApproval.query.filter_by(
            subscriber_id=subscriber.id,
            status='pending'
        ).order_by(DepositApproval.created_at.desc()).first()
        
        if not deposit_approval:
            await update.message.reply_text(
                "❌ **No Pending Payment Found**\n\n"
                "No pending crypto payment found for your subscription.\n"
                "If you've already submitted a transaction hash, please wait for admin approval.\n"
                "Use /status to check your subscription status."
            )
            return
        
        # Check if transaction hash already exists
        if deposit_approval.transaction_hash:
            hash_escaped = escape_markdown(deposit_approval.transaction_hash)
            new_hash_escaped = escape_markdown(transaction_hash)
            message = (
                f"⚠️ **Transaction Hash Already Submitted**\n\n"
                f"Previous hash: `{hash_escaped}`\n"
                f"New hash: `{new_hash_escaped}`\n\n"
                f"Updating with new transaction hash..."
            )
            try:
                await update.message.reply_text(message, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(
                    f"⚠️ Transaction Hash Already Submitted\n\n"
                    f"Previous: {deposit_approval.transaction_hash}\n"
                    f"New: {transaction_hash}\n\n"
                    f"Updating with new transaction hash..."
                )
        
        # Update transaction hash in both DepositApproval and Subscriber
        deposit_approval.transaction_hash = transaction_hash
        subscriber.crypto_transaction_hash = transaction_hash
        db.session.commit()
        
        # Send confirmation message
        hash_escaped = escape_markdown(transaction_hash)
        phone_escaped = escape_markdown(subscriber.phone_number)
        currency_escaped = escape_markdown(deposit_approval.currency)
        amount_escaped = escape_markdown(str(deposit_approval.amount))
        
        message = (
            f"✅ **Payment Verification Submitted!**\n\n"
            f"📱 Phone: {phone_escaped}\n"
            f"₿ Currency: {currency_escaped}\n"
            f"💰 Amount: ${amount_escaped}\n"
            f"🔗 Transaction Hash: `{hash_escaped}`\n\n"
            f"⏳ Your payment is now pending admin approval.\n"
            f"You will receive a confirmation message once approved."
        )
        
        try:
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(
                f"✅ Payment Verification Submitted!\n\n"
                f"Phone: {subscriber.phone_number}\n"
                f"Currency: {deposit_approval.currency}\n"
                f"Amount: ${deposit_approval.amount}\n"
                f"Transaction Hash: {transaction_hash}\n\n"
                f"⏳ Your payment is now pending admin approval.\n"
                f"You will receive a confirmation message once approved."
            )
        
        logger.info(f"Payment verification submitted by user {user.id}: {transaction_hash}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message."""
    help_text = (
        "🤖 **Subscription Service Bot Commands**\n\n"
        "/start - Start subscription process\n"
        "/status - Check your subscription status\n"
        "/verify_payment - Verify crypto payment (with transaction hash)\n"
        "/help - Show this help message\n"
        "/support - Contact customer support\n"
        "/cancel - Cancel current operation\n\n"
        "**Features:**\n"
        "• SMS subscription service\n"
        "• Multiple pricing plans available\n"
        "• Multiple payment methods (Stripe, PayPal, Crypto)\n"
        "• Scheduled message delivery\n"
        "• Timezone-matched message delivery\n\n"
        "**Crypto Payment:**\n"
        "After sending crypto payment, use:\n"
        "`/verify_payment YOUR_TRANSACTION_HASH`\n\n"
        "Need help? Use /support to contact us."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support contact information."""
    from app import app
    with app.app_context():
        # Get support info from group or config
        group_id = Config.DEFAULT_GROUP_ID
        support_telegram = Config.SUPPORT_TELEGRAM_USERNAME
        support_email = Config.SUPPORT_EMAIL
        
        if group_id:
            try:
                group = ServiceGroup.query.filter_by(id=group_id, is_active=True).first()
                if group:
                    if group.support_telegram_username:
                        support_telegram = group.support_telegram_username
                    if group.support_email:
                        support_email = group.support_email
            except Exception as e:
                logger.warning(f"Could not load group {group_id}: {e}")
        
        support_text = "📞 **Customer Support**\n\n"
        
        if support_telegram:
            # Format Telegram username properly
            if not support_telegram.startswith('@'):
                support_telegram = f"@{support_telegram}"
            support_text += f"💬 Telegram: {support_telegram}\n"
        
        if support_email:
            support_text += f"📧 Email: {support_email}\n"
        
        if not support_telegram and not support_email:
            support_text += "Please contact the administrator for support.\n"
            support_text += "You can also use /help for more information."
        else:
            support_text += "\nWe're here to help! Reach out if you have any questions or issues."
        
        await update.message.reply_text(support_text, parse_mode='Markdown')

def setup_telegram_bot(app_context=None):
    """Set up and start the Telegram bot."""
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return None
    
    try:
        # Build application - workaround for weak reference issue in python-telegram-bot v21.0
        # The issue is that Application objects can't be weak referenced in some contexts
        # Solution: Build without job_queue first, then manually disable it
        builder = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).concurrent_updates(True)
        
        # Try to build without job_queue
        try:
            application = builder.build()
            # After build, we can access and modify job_queue if needed
            # But the issue happens during build, so we need a different approach
        except TypeError as e:
            if "weak reference" in str(e):
                # If weak reference fails, try to monkey-patch the JobQueue class
                import telegram.ext._jobqueue
                original_set_application = telegram.ext._jobqueue.JobQueue.set_application
                
                def patched_set_application(self, application):
                    # Store direct reference instead of weak reference
                    self._application = application
                
                telegram.ext._jobqueue.JobQueue.set_application = patched_set_application
                
                # Try building again
                application = builder.build()
                
                # Restore original method
                telegram.ext._jobqueue.JobQueue.set_application = original_set_application
            else:
                raise
        
        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                PHONE_NUMBER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number_handler)
                ],
                CARRIER: [
                    CallbackQueryHandler(carrier_callback, pattern="^carrier_")
                ],
                EMAIL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, email_handler),
                    CommandHandler('skip', skip_email)
                ],
                NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler),
                    CommandHandler('skip', skip_name)
                ],
                TIMEZONE_SELECTION: [
                    CallbackQueryHandler(timezone_selection_callback, pattern="^tz_"),
                    CommandHandler('skip', skip_timezone)
                ],
                DELIVERY_PREFERENCE: [
                    CallbackQueryHandler(delivery_preference_callback, pattern="^delivery_")
                ],
                PLAN_SELECTION: [
                    CallbackQueryHandler(plan_selection_callback, pattern="^plan_")
                ],
                DISCOUNT_CODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, discount_code_handler),
                    CommandHandler('skip', skip_discount_code)
                ],
                PAYMENT_METHOD: [
                    CallbackQueryHandler(payment_method_callback, pattern="^payment_")
                ],
                CRYPTO_CURRENCY: [
                    CallbackQueryHandler(payment_method_callback, pattern="^crypto_")
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            per_chat=True,  # Track per chat
            per_user=True   # Track per user
        )
        
        # Add handlers - IMPORTANT: Add conversation handler first, then other handlers
        application.add_handler(conv_handler)
        
        # Add standalone command handlers (outside conversation)
        application.add_handler(CommandHandler('status', status))
        application.add_handler(CommandHandler('verify_payment', verify_payment))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('support', support_command))
        
        return application
    except Exception as e:
        logger.error(f"Error setting up Telegram bot: {e}", exc_info=True)
        return None

async def send_telegram_notification_async(subscriber, message, bot_token):
    """Send a notification to a subscriber via Telegram (async)."""
    if not subscriber.telegram_user_id:
        return False
    
    try:
        from telegram import Bot
        bot = Bot(token=bot_token)
        # Try with Markdown first, fallback to plain text if parsing fails
        try:
            await bot.send_message(
                chat_id=subscriber.telegram_user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as parse_error:
            # If Markdown parsing fails, send as plain text
            logger.warning(f"Markdown parsing failed, sending as plain text: {parse_error}")
            await bot.send_message(
                chat_id=subscriber.telegram_user_id,
                text=message
            )
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

def send_telegram_notification(subscriber, message):
    """Send a notification to a subscriber via Telegram (sync wrapper)."""
    if not subscriber.telegram_user_id or not Config.TELEGRAM_BOT_TOKEN:
        return False
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            send_telegram_notification_async(subscriber, message, Config.TELEGRAM_BOT_TOKEN)
        )
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

def format_price(price):
    """Format price without trailing zeros (e.g., 1.60 -> 1.6, 1.55 -> 1.55)."""
    if price is None:
        return "0"
    # Format to 2 decimal places, then remove trailing zeros
    formatted = f"{float(price):.2f}"
    # Remove trailing zeros and decimal point if not needed
    if '.' in formatted:
        formatted = formatted.rstrip('0').rstrip('.')
    return formatted

TIMEZONE_OPTIONS = [
    ('UTC-12', -720),
    ('UTC-11', -660),
    ('UTC-10', -600),
    ('UTC-9:30', -570),
    ('UTC-9', -540),
    ('UTC-8', -480),
    ('UTC-7', -420),
    ('UTC-6', -360),
    ('UTC-5', -300),
    ('UTC-4:30', -270),
    ('UTC-4', -240),
    ('UTC-3:30', -210),
    ('UTC-3', -180),
    ('UTC-2', -120),
    ('UTC-1', -60),
    ('UTC', 0),
    ('UTC+1', 60),
    ('UTC+2', 120),
    ('UTC+3', 180),
    ('UTC+3:30', 210),
    ('UTC+4', 240),
    ('UTC+4:30', 270),
    ('UTC+5', 300),
    ('UTC+5:30', 330),
    ('UTC+5:45', 345),
    ('UTC+6', 360),
    ('UTC+6:30', 390),
    ('UTC+7', 420),
    ('UTC+8', 480),
    ('UTC+8:45', 525),
    ('UTC+9', 540),
    ('UTC+9:30', 570),
    ('UTC+10', 600),
    ('UTC+10:30', 630),
    ('UTC+11', 660),
    ('UTC+11:30', 690),
    ('UTC+12', 720),
    ('UTC+12:45', 765),
    ('UTC+13', 780),
    ('UTC+14', 840),
]

TIMEZONE_LOOKUP = {offset: label for label, offset in TIMEZONE_OPTIONS}

def get_timezone_keyboard():
    """Build inline keyboard for timezone selection."""
    keyboard = []
    row = []
    for label, offset in TIMEZONE_OPTIONS:
        row.append(InlineKeyboardButton(label, callback_data=f"tz_{offset}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def format_timezone_display(label, offset_minutes):
    if offset_minutes is None:
        offset_minutes = 0
    sign = '+' if offset_minutes >= 0 else '-'
    minutes_abs = abs(offset_minutes)
    hours = minutes_abs // 60
    mins = minutes_abs % 60
    offset_text = f"UTC{sign}{hours:02d}:{mins:02d}"
    if label and label != 'UTC':
        return f"{label} ({offset_text})"
    return offset_text

