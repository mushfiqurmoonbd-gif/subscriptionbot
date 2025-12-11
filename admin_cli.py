#!/usr/bin/env python3
"""
Admin CLI for Subscription Service Bot
Command-line interface for managing subscribers, messages, and subscriptions.
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from tabulate import tabulate
import argparse
from flask import Flask
from config import Config
from models import db, Subscriber, ScheduledMessage, Subscription, DepositApproval, SubscriptionPlan, DiscountCode
from plan_manager import get_active_plans, get_plan_by_id, validate_discount_code, apply_discount_code, increment_discount_code_usage
from sms_sender import send_sms_to_subscriber
from crypto_manager import activate_crypto_subscription
from telegram_bot import send_telegram_notification
from delivery_messages import get_delivery_message

# Initialize Flask app for database access
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def format_date(date):
    """Format datetime for display."""
    if date:
        return date.strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A'

def format_status(status):
    """Format status with color indicators."""
    status_map = {
        'active': '✓ Active',
        'pending': '⏳ Pending',
        'cancelled': '✗ Cancelled',
        'canceled': '✗ Cancelled',
        'expired': '✗ Expired',
        'inactive': '✗ Inactive',
        'pending_payment': '⏳ Pending Payment'
    }
    return status_map.get(status, status.capitalize() if status else 'Unknown')

def format_timezone_display(label, offset_minutes):
    """Return human-friendly timezone text."""
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

def list_subscribers(args):
    """List all subscribers."""
    with app.app_context():
        subscribers = Subscriber.query.all()
        
        if not subscribers:
            print("No subscribers found.")
            return
        
        # Filter by status if provided
        if args.status:
            subscribers = [s for s in subscribers if s.subscription_status == args.status]
        
        # Prepare table data
        table_data = []
        for sub in subscribers:
            table_data.append([
                sub.id,
                sub.name,
                sub.phone_number,
                sub.carrier,
                sub.email,
                format_status(sub.subscription_status),
                sub.payment_method or 'N/A',
                format_date(sub.created_at)
            ])
        
        headers = ['ID', 'Name', 'Phone', 'Carrier', 'Email', 'Status', 'Payment', 'Created']
        print(f"\nTotal Subscribers: {len(table_data)}")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Summary statistics
        status_counts = {}
        payment_counts = {}
        for sub in subscribers:
            status_counts[sub.subscription_status] = status_counts.get(sub.subscription_status, 0) + 1
            if sub.payment_method:
                payment_counts[sub.payment_method] = payment_counts.get(sub.payment_method, 0) + 1
        
        print("\n--- Status Summary ---")
        for status, count in status_counts.items():
            print(f"  {format_status(status)}: {count}")
        
        print("\n--- Payment Method Summary ---")
        for method, count in payment_counts.items():
            print(f"  {method}: {count}")

def show_subscriber(args):
    """Show detailed information about a subscriber."""
    with app.app_context():
        subscriber = Subscriber.query.get(args.id)
        
        if not subscriber:
            print(f"Subscriber with ID {args.id} not found.")
            return
        
        print(f"\n{'='*60}")
        print(f"SUBSCRIBER DETAILS - ID: {subscriber.id}")
        print(f"{'='*60}\n")
        
        print(f"Name:              {subscriber.name}")
        print(f"Phone Number:      {subscriber.phone_number}")
        print(f"Carrier:           {subscriber.carrier}")
        print(f"Email:              {subscriber.email}")
        print(f"Status:             {format_status(subscriber.subscription_status)}")
        print(f"Payment Method:    {subscriber.payment_method or 'N/A'}")
        print(f"Created At:         {format_date(subscriber.created_at)}")
        
        if subscriber.telegram_user_id:
            print(f"Telegram User ID:   {subscriber.telegram_user_id}")
            print(f"Telegram Username:  {subscriber.telegram_username or 'N/A'}")
        
        # Payment method specific info
        if subscriber.payment_method == 'stripe':
            print(f"\n--- Stripe Information ---")
            print(f"Stripe Customer ID: {subscriber.stripe_customer_id or 'N/A'}")
            print(f"Stripe Subscription ID: {subscriber.stripe_subscription_id or 'N/A'}")
        
        elif subscriber.payment_method == 'paypal':
            print(f"\n--- PayPal Information ---")
            print(f"PayPal Subscription ID: {subscriber.paypal_subscription_id or 'N/A'}")
            print(f"PayPal Billing Agreement ID: {subscriber.paypal_billing_agreement_id or 'N/A'}")
        
        elif subscriber.payment_method == 'crypto':
            print(f"\n--- Cryptocurrency Information ---")
            print(f"Payment Address: {subscriber.crypto_payment_address or 'N/A'}")
            print(f"Transaction Hash: {subscriber.crypto_transaction_hash or 'N/A'}")
        
        # Show subscriptions
        subscriptions = Subscription.query.filter_by(subscriber_id=subscriber.id).all()
        if subscriptions:
            print(f"\n--- Subscriptions ({len(subscriptions)}) ---")
            sub_data = []
            for sub in subscriptions:
                sub_data.append([
                    sub.id,
                    format_status(sub.status),
                    sub.payment_method,
                    format_date(sub.start_date),
                    format_date(sub.end_date),
                    format_date(sub.created_at)
                ])
            headers = ['ID', 'Status', 'Payment', 'Start', 'End', 'Created']
            print(tabulate(sub_data, headers=headers, tablefmt='grid'))
        
        # Show scheduled messages
        scheduled = ScheduledMessage.query.filter_by(subscriber_id=subscriber.id).all()
        if scheduled:
            print(f"\n--- Scheduled Messages ({len(scheduled)}) ---")
            msg_data = []
            for msg in scheduled:
                msg_data.append([
                    msg.id,
                    msg.message[:50] + '...' if len(msg.message) > 50 else msg.message,
                    format_date(msg.scheduled_time),
                    '✓ Sent' if msg.sent else '⏳ Pending',
                    format_date(msg.sent_at) if msg.sent_at else 'N/A'
                ])
            headers = ['ID', 'Message', 'Scheduled', 'Status', 'Sent At']
            print(tabulate(msg_data, headers=headers, tablefmt='grid'))

def send_message(args):
    """Send a message to a subscriber."""
    with app.app_context():
        subscriber = Subscriber.query.get(args.id)
        
        if not subscriber:
            print(f"Subscriber with ID {args.id} not found.")
            return
        
        message = args.message
        if not message:
            print("Error: Message text is required.")
            return
        
        print(f"\nSending message to {subscriber.name} ({subscriber.phone_number})...")
        print(f"Message: {message}")
        
        if args.confirm or input("\nConfirm send? (y/N): ").lower() == 'y':
            try:
                success = send_sms_to_subscriber(subscriber, message)
                if success:
                    print("\n✓ Message sent successfully!")
                else:
                    print("\n✗ Failed to send message. Check logs for details.")
            except Exception as e:
                print(f"\n✗ Error sending message: {str(e)}")
        else:
            print("Cancelled.")

def schedule_message(args):
    """Schedule a message for a subscriber."""
    with app.app_context():
        subscriber = Subscriber.query.get(args.id)
        
        if not subscriber:
            print(f"Subscriber with ID {args.id} not found.")
            return
        
        message = args.message
        scheduled_time = args.time
        
        if not message:
            print("Error: Message text is required.")
            return
        
        try:
            # Parse scheduled time
            if scheduled_time:
                scheduled_datetime = datetime.fromisoformat(scheduled_time)
            else:
                # Default to 1 hour from now
                scheduled_datetime = datetime.now() + timedelta(hours=1)
            
            timezone_offset = subscriber.timezone_offset_minutes or 0
            timezone_label = subscriber.timezone_label or 'UTC'

            if scheduled_datetime.tzinfo is not None:
                utc_datetime = scheduled_datetime.astimezone(timezone.utc)
                local_display = (utc_datetime + timedelta(minutes=timezone_offset)).replace(tzinfo=None)
                utc_naive = utc_datetime.replace(tzinfo=None)
            else:
                local_display = scheduled_datetime
                utc_naive = scheduled_datetime - timedelta(minutes=timezone_offset)

            # Create scheduled message
            scheduled_msg = ScheduledMessage(
                subscriber_id=subscriber.id,
                message=message,
                scheduled_time=utc_naive,
                timezone_offset_minutes=timezone_offset,
                timezone_label=timezone_label
            )
            
            db.session.add(scheduled_msg)
            db.session.commit()
            
            timezone_display = format_timezone_display(timezone_label, timezone_offset)
            print(f"\n✓ Message scheduled successfully!")
            print(f"  Subscriber: {subscriber.name}")
            print(f"  Scheduled Time (local): {format_date(local_display)} {timezone_display}")
            print(f"  Scheduled Time (UTC): {format_date(utc_naive)}")
            print(f"  Message ID: {scheduled_msg.id}")
            
        except ValueError as e:
            print(f"Error: Invalid time format. Use ISO format: YYYY-MM-DDTHH:MM:SS")
        except Exception as e:
            print(f"Error scheduling message: {str(e)}")
            db.session.rollback()

def update_status(args):
    """Update subscriber status."""
    with app.app_context():
        subscriber = Subscriber.query.get(args.id)
        
        if not subscriber:
            print(f"Subscriber with ID {args.id} not found.")
            return
        
        old_status = subscriber.subscription_status
        subscriber.subscription_status = args.status
        db.session.commit()
        
        print(f"\n✓ Status updated successfully!")
        print(f"  Subscriber: {subscriber.name} (ID: {subscriber.id})")
        print(f"  Old Status: {format_status(old_status)}")
        print(f"  New Status: {format_status(args.status)}")

def delete_subscriber(args):
    """Delete a subscriber."""
    with app.app_context():
        subscriber = Subscriber.query.get(args.id)
        
        if not subscriber:
            print(f"Subscriber with ID {args.id} not found.")
            return
        
        print(f"\nSubscriber to delete:")
        print(f"  ID: {subscriber.id}")
        print(f"  Name: {subscriber.name}")
        print(f"  Phone: {subscriber.phone_number}")
        print(f"  Status: {format_status(subscriber.subscription_status)}")
        
        if args.force or input("\nAre you sure you want to delete this subscriber? (yes/N): ").lower() == 'yes':
            # Delete related records
            ScheduledMessage.query.filter_by(subscriber_id=subscriber.id).delete()
            Subscription.query.filter_by(subscriber_id=subscriber.id).delete()
            
            db.session.delete(subscriber)
            db.session.commit()
            
            print("\n✓ Subscriber deleted successfully!")
        else:
            print("Cancelled.")

def list_messages(args):
    """List scheduled messages."""
    with app.app_context():
        messages = ScheduledMessage.query.order_by(ScheduledMessage.scheduled_time.desc()).all()
        
        if not messages:
            print("No scheduled messages found.")
            return
        
        # Filter by status
        if args.sent:
            messages = [m for m in messages if m.sent]
        elif args.pending:
            messages = [m for m in messages if not m.sent]
        
        # Filter by subscriber
        if args.subscriber_id:
            messages = [m for m in messages if m.subscriber_id == args.subscriber_id]
        
        table_data = []
        for msg in messages:
            subscriber = Subscriber.query.get(msg.subscriber_id)
            subscriber_name = subscriber.name if subscriber else f"ID:{msg.subscriber_id}"
            
            table_data.append([
                msg.id,
                subscriber_name,
                msg.message[:40] + '...' if len(msg.message) > 40 else msg.message,
                format_date(msg.scheduled_time),
                '✓ Sent' if msg.sent else '⏳ Pending',
                format_date(msg.sent_at) if msg.sent_at else 'N/A'
            ])
        
        headers = ['ID', 'Subscriber', 'Message', 'Scheduled', 'Status', 'Sent At']
        print(f"\nTotal Messages: {len(table_data)}")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))

def stats(args):
    """Show statistics."""
    with app.app_context():
        print(f"\n{'='*60}")
        print("SUBSCRIPTION SERVICE STATISTICS")
        print(f"{'='*60}\n")
        
        # Subscriber statistics
        total_subscribers = Subscriber.query.count()
        active_subscribers = Subscriber.query.filter_by(subscription_status='active').count()
        pending_subscribers = Subscriber.query.filter_by(subscription_status='pending').count()
        cancelled_subscribers = Subscriber.query.filter_by(subscription_status='cancelled').count()
        
        print("--- Subscribers ---")
        print(f"  Total:           {total_subscribers}")
        print(f"  Active:          {active_subscribers}")
        print(f"  Pending:         {pending_subscribers}")
        print(f"  Cancelled:       {cancelled_subscribers}")
        
        # Payment method statistics
        stripe_count = Subscriber.query.filter_by(payment_method='stripe').count()
        paypal_count = Subscriber.query.filter_by(payment_method='paypal').count()
        crypto_count = Subscriber.query.filter_by(payment_method='crypto').count()
        
        print("\n--- Payment Methods ---")
        print(f"  Stripe:          {stripe_count}")
        print(f"  PayPal:          {paypal_count}")
        print(f"  Cryptocurrency:  {crypto_count}")
        
        # Message statistics
        total_messages = ScheduledMessage.query.count()
        sent_messages = ScheduledMessage.query.filter_by(sent=True).count()
        pending_messages = ScheduledMessage.query.filter_by(sent=False).count()
        
        print("\n--- Messages ---")
        print(f"  Total Scheduled: {total_messages}")
        print(f"  Sent:            {sent_messages}")
        print(f"  Pending:         {pending_messages}")
        
        # Subscription statistics
        total_subscriptions = Subscription.query.count()
        active_subscriptions = Subscription.query.filter_by(status='active').count()
        
        print("\n--- Subscriptions ---")
        print(f"  Total:           {total_subscriptions}")
        print(f"  Active:           {active_subscriptions}")
        
        # Recent activity
        print("\n--- Recent Activity ---")
        recent_subscribers = Subscriber.query.order_by(Subscriber.created_at.desc()).limit(5).all()
        if recent_subscribers:
            print("  Recent Subscribers:")
            for sub in recent_subscribers:
                print(f"    - {sub.name} ({sub.phone_number}) - {format_date(sub.created_at)}")
        
        recent_messages = ScheduledMessage.query.order_by(ScheduledMessage.scheduled_time.desc()).limit(5).all()
        if recent_messages:
            print("  Recent Messages:")
            for msg in recent_messages:
                sub = Subscriber.query.get(msg.subscriber_id)
                sub_name = sub.name if sub else f"ID:{msg.subscriber_id}"
                status = '✓ Sent' if msg.sent else '⏳ Pending'
                print(f"    - {sub_name}: {msg.message[:30]}... - {status} - {format_date(msg.scheduled_time)}")

def export_subscribers(args):
    """Export subscribers to CSV."""
    import csv
    
    with app.app_context():
        subscribers = Subscriber.query.all()
        
        if not subscribers:
            print("No subscribers to export.")
            return
        
        filename = args.output or f"subscribers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'name', 'phone_number', 'carrier', 'email', 'status', 
                         'payment_method', 'created_at', 'telegram_user_id', 'telegram_username']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for sub in subscribers:
                writer.writerow({
                    'id': sub.id,
                    'name': sub.name,
                    'phone_number': sub.phone_number,
                    'carrier': sub.carrier,
                    'email': sub.email,
                    'status': sub.subscription_status,
                    'payment_method': sub.payment_method or '',
                    'created_at': format_date(sub.created_at),
                    'telegram_user_id': sub.telegram_user_id or '',
                    'telegram_username': sub.telegram_username or ''
                })
        
        print(f"\n✓ Exported {len(subscribers)} subscribers to {filename}")

def list_pending_payments(args):
    """List all pending payments."""
    with app.app_context():
        print(f"\n{'='*60}")
        print("PENDING PAYMENTS")
        print(f"{'='*60}\n")
        
        # Get pending deposit approvals (manual crypto payments)
        pending_deposits = DepositApproval.query.filter_by(status='pending').all()
        
        # Get pending subscribers (any payment method)
        pending_subscribers = Subscriber.query.filter_by(subscription_status='pending').all()
        
        if not pending_deposits and not pending_subscribers:
            print("No pending payments found.")
            return
        
        # Display deposit approvals
        if pending_deposits:
            print("--- Manual Crypto Payment Requests ---")
            deposit_data = []
            for deposit in pending_deposits:
                subscriber = deposit.subscriber
                deposit_data.append([
                    deposit.id,
                    subscriber.name if subscriber else f"ID:{deposit.subscriber_id}",
                    subscriber.phone_number if subscriber else 'N/A',
                    deposit.currency,
                    f"${float(deposit.amount):.2f}",
                    deposit.wallet_address[:20] + '...' if len(deposit.wallet_address) > 20 else deposit.wallet_address,
                    deposit.transaction_hash[:20] + '...' if deposit.transaction_hash and len(deposit.transaction_hash) > 20 else (deposit.transaction_hash or 'N/A'),
                    format_date(deposit.created_at)
                ])
            headers = ['ID', 'Name', 'Phone', 'Currency', 'Amount', 'Wallet', 'TX Hash', 'Created']
            print(tabulate(deposit_data, headers=headers, tablefmt='grid'))
            print()
        
        # Display pending subscribers
        if pending_subscribers:
            print("--- Pending Subscribers ---")
            subscriber_data = []
            for sub in pending_subscribers:
                # Skip if already shown in deposit approvals
                if sub.payment_method == 'crypto':
                    has_pending_deposit = any(d.subscriber_id == sub.id for d in pending_deposits)
                    if has_pending_deposit:
                        continue
                
                # Add payment method specific info
                payment_info = sub.payment_method or 'N/A'
                if sub.payment_method == 'stripe' and sub.stripe_subscription_id:
                    payment_info = f"{sub.payment_method} ({sub.stripe_subscription_id[:20]}...)" if len(sub.stripe_subscription_id) > 20 else f"{sub.payment_method} ({sub.stripe_subscription_id})"
                elif sub.payment_method == 'paypal' and sub.paypal_subscription_id:
                    payment_info = f"{sub.payment_method} ({sub.paypal_subscription_id[:20]}...)" if len(sub.paypal_subscription_id) > 20 else f"{sub.payment_method} ({sub.paypal_subscription_id})"
                elif sub.payment_method == 'paypal' and sub.paypal_billing_agreement_id:
                    payment_info = f"{sub.payment_method} ({sub.paypal_billing_agreement_id[:20]}...)" if len(sub.paypal_billing_agreement_id) > 20 else f"{sub.payment_method} ({sub.paypal_billing_agreement_id})"
                
                subscriber_data.append([
                    sub.id,
                    sub.name,
                    sub.phone_number,
                    payment_info,
                    format_date(sub.created_at)
                ])
            
            if subscriber_data:
                headers = ['ID', 'Name', 'Phone', 'Payment Method', 'Created']
                print(tabulate(subscriber_data, headers=headers, tablefmt='grid'))
        
        print(f"\nTotal Pending: {len(pending_deposits) + len([s for s in pending_subscribers if not any(d.subscriber_id == s.id for d in pending_deposits)])}")

def approve_payment(args):
    """
    Approve a pending payment.
    
    Works for:
    - Crypto payments (DepositApproval records)
    - Stripe payments (if webhook fails, can manually approve)
    - PayPal payments (if webhook fails, can manually approve)
    
    When approving Stripe/PayPal payments manually, the subscription will be
    activated in the database. Make sure payment was actually received before approving.
    """
    with app.app_context():
        # Check if it's a deposit approval
        deposit = DepositApproval.query.get(args.id)
        
        if deposit:
            if deposit.status != 'pending':
                print(f"Error: Deposit approval {args.id} is not pending (current status: {deposit.status})")
                return
            
            subscriber = deposit.subscriber
            if not subscriber:
                print(f"Error: Subscriber not found for deposit approval {args.id}")
                return
            
            # Approve the deposit
            deposit.status = 'approved'
            deposit.reviewed_at = datetime.utcnow()
            deposit.reviewed_by = args.admin or 'admin_cli'
            if args.notes:
                deposit.admin_notes = args.notes
            
            # Activate the subscription
            if subscriber.payment_method == 'crypto':
                activate_crypto_subscription(subscriber, deposit.transaction_hash)
            else:
                subscriber.subscription_status = 'active'
            
            db.session.commit()
            
            # Send Telegram notification if user has Telegram ID
            telegram_sent = False
            if subscriber.telegram_user_id:
                try:
                    # Determine language (English only)
                    language = 'en'
                    
                    # Send payment confirmation message
                    confirmation_msg = get_delivery_message('payment_approved', language)
                    if subscriber.name:
                        confirmation_msg = f"Hi {subscriber.name}!\n\n{confirmation_msg}"
                    
                    # Send welcome message
                    welcome_msg = get_delivery_message('welcome', language)
                    if subscriber.name:
                        welcome_msg = f"Hi {subscriber.name}!\n\n{welcome_msg}"
                    
                    # Send both messages
                    send_telegram_notification(subscriber, confirmation_msg)
                    send_telegram_notification(subscriber, welcome_msg)
                    telegram_sent = True
                    print(f"  ✓ Telegram notification sent to user")
                except Exception as tg_error:
                    print(f"  ⚠ Warning: Failed to send Telegram notification: {str(tg_error)}")
            
            print(f"\n✓ Payment approved successfully!")
            print(f"  Deposit Approval ID: {deposit.id}")
            print(f"  Subscriber: {subscriber.name} (ID: {subscriber.id})")
            print(f"  Amount: ${float(deposit.amount):.2f} {deposit.currency}")
            print(f"  Status: Active")
            if not subscriber.telegram_user_id:
                print(f"  Note: No Telegram ID found, notification not sent")
            return
        
        # Check if it's a pending subscriber
        subscriber = Subscriber.query.get(args.id)
        if subscriber:
            if subscriber.subscription_status != 'pending':
                print(f"Error: Subscriber {args.id} is not pending (current status: {subscriber.subscription_status})")
                return
            
            subscriber.subscription_status = 'active'
            
            # Create or update subscription record based on payment method
            sub_record = Subscription.query.filter_by(
                subscriber_id=subscriber.id,
                payment_method=subscriber.payment_method
            ).first()
            
            if not sub_record:
                # Create new subscription record
                sub_record = Subscription(
                    subscriber_id=subscriber.id,
                    payment_method=subscriber.payment_method,
                    status='active',
                    current_period_start=datetime.utcnow(),
                    current_period_end=datetime.utcnow() + timedelta(days=30)
                )
                
                # Add payment method specific IDs
                if subscriber.payment_method == 'stripe':
                    sub_record.stripe_subscription_id = subscriber.stripe_subscription_id
                    sub_record.stripe_customer_id = subscriber.stripe_customer_id
                elif subscriber.payment_method == 'paypal':
                    sub_record.paypal_subscription_id = subscriber.paypal_subscription_id
                    sub_record.paypal_billing_agreement_id = subscriber.paypal_billing_agreement_id
                elif subscriber.payment_method == 'crypto':
                    sub_record.crypto_payment_id = subscriber.crypto_payment_address
                    sub_record.crypto_transaction_hash = subscriber.crypto_transaction_hash
                
                db.session.add(sub_record)
            else:
                # Update existing subscription record
                sub_record.status = 'active'
                sub_record.current_period_start = datetime.utcnow()
                sub_record.current_period_end = datetime.utcnow() + timedelta(days=30)
                
                # Update payment method specific IDs if missing
                if subscriber.payment_method == 'stripe':
                    if subscriber.stripe_subscription_id:
                        sub_record.stripe_subscription_id = subscriber.stripe_subscription_id
                    if subscriber.stripe_customer_id:
                        sub_record.stripe_customer_id = subscriber.stripe_customer_id
                elif subscriber.payment_method == 'paypal':
                    if subscriber.paypal_subscription_id:
                        sub_record.paypal_subscription_id = subscriber.paypal_subscription_id
                    if subscriber.paypal_billing_agreement_id:
                        sub_record.paypal_billing_agreement_id = subscriber.paypal_billing_agreement_id
            
            db.session.commit()
            
            # Send Telegram notification if user has Telegram ID
            telegram_sent = False
            if subscriber.telegram_user_id:
                try:
                    # Determine language (English only)
                    language = 'en'
                    
                    # Send payment confirmation message
                    confirmation_msg = get_delivery_message('payment_approved', language)
                    if subscriber.name:
                        confirmation_msg = f"Hi {subscriber.name}!\n\n{confirmation_msg}"
                    
                    # Send welcome message
                    welcome_msg = get_delivery_message('welcome', language)
                    if subscriber.name:
                        welcome_msg = f"Hi {subscriber.name}!\n\n{welcome_msg}"
                    
                    # Send both messages
                    send_telegram_notification(subscriber, confirmation_msg)
                    send_telegram_notification(subscriber, welcome_msg)
                    telegram_sent = True
                    print(f"  ✓ Telegram notification sent to user")
                except Exception as tg_error:
                    print(f"  ⚠ Warning: Failed to send Telegram notification: {str(tg_error)}")
            
            print(f"\n✓ Payment approved successfully!")
            print(f"  Subscriber: {subscriber.name} (ID: {subscriber.id})")
            print(f"  Payment Method: {subscriber.payment_method}")
            if subscriber.payment_method == 'stripe' and subscriber.stripe_subscription_id:
                print(f"  Stripe Subscription ID: {subscriber.stripe_subscription_id}")
            elif subscriber.payment_method == 'paypal' and subscriber.paypal_subscription_id:
                print(f"  PayPal Subscription ID: {subscriber.paypal_subscription_id}")
            print(f"  Status: Active")
            if not subscriber.telegram_user_id:
                print(f"  Note: No Telegram ID found, notification not sent")
            return
        
        print(f"Error: No pending payment found with ID {args.id}")

def reject_payment(args):
    """Reject a pending payment."""
    with app.app_context():
        # Check if it's a deposit approval
        deposit = DepositApproval.query.get(args.id)
        
        if deposit:
            if deposit.status != 'pending':
                print(f"Error: Deposit approval {args.id} is not pending (current status: {deposit.status})")
                return
            
            subscriber = deposit.subscriber
            
            # Reject the deposit
            deposit.status = 'rejected'
            deposit.reviewed_at = datetime.utcnow()
            deposit.reviewed_by = args.admin or 'admin_cli'
            deposit.admin_notes = args.reason or 'Payment rejected by admin'
            
            # Update subscriber status
            if subscriber:
                subscriber.subscription_status = 'inactive'
            
            db.session.commit()
            
            print(f"\n✓ Payment rejected successfully!")
            print(f"  Deposit Approval ID: {deposit.id}")
            if subscriber:
                print(f"  Subscriber: {subscriber.name} (ID: {subscriber.id})")
            print(f"  Amount: ${float(deposit.amount):.2f} {deposit.currency}")
            print(f"  Reason: {deposit.admin_notes}")
            return
        
        # Check if it's a pending subscriber
        subscriber = Subscriber.query.get(args.id)
        if subscriber:
            if subscriber.subscription_status != 'pending':
                print(f"Error: Subscriber {args.id} is not pending (current status: {subscriber.subscription_status})")
                return
            
            subscriber.subscription_status = 'inactive'
            
            # Update subscription record if exists
            sub_record = Subscription.query.filter_by(
                subscriber_id=subscriber.id,
                payment_method=subscriber.payment_method
            ).first()
            
            if sub_record:
                sub_record.status = 'cancelled'
            
            db.session.commit()
            
            print(f"\n✓ Payment rejected successfully!")
            print(f"  Subscriber: {subscriber.name} (ID: {subscriber.id})")
            print(f"  Payment Method: {subscriber.payment_method}")
            if subscriber.payment_method == 'stripe' and subscriber.stripe_subscription_id:
                print(f"  Stripe Subscription ID: {subscriber.stripe_subscription_id}")
                print(f"  Note: Stripe subscription may need to be canceled manually in Stripe dashboard")
            elif subscriber.payment_method == 'paypal' and subscriber.paypal_subscription_id:
                print(f"  PayPal Subscription ID: {subscriber.paypal_subscription_id}")
                print(f"  Note: PayPal subscription may need to be canceled manually in PayPal dashboard")
            print(f"  Reason: {args.reason or 'Payment rejected by admin'}")
            print(f"  Status: Inactive")
            return
        
        print(f"Error: No pending payment found with ID {args.id}")

# ========== Plan Management Functions ==========

def list_plans(args):
    """List all subscription plans."""
    with app.app_context():
        plans = SubscriptionPlan.query.order_by(SubscriptionPlan.display_order).all()
        
        if not plans:
            print("No subscription plans found.")
            return
        
        table_data = []
        for plan in plans:
            trial_info = f"{plan.trial_days} days" if plan.has_trial else "No"
            status = "✓ Active" if plan.is_active else "✗ Inactive"
            table_data.append([
                plan.id,
                plan.name,
                f"${float(plan.price):.2f}",
                plan.currency,
                trial_info,
                status,
                plan.display_order,
                format_date(plan.created_at)
            ])
        
        headers = ['ID', 'Name', 'Price', 'Currency', 'Trial', 'Status', 'Order', 'Created']
        print(f"\nTotal Plans: {len(table_data)}")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))

def create_plan(args):
    """Create a new subscription plan."""
    with app.app_context():
        # Check if plan name already exists
        existing = SubscriptionPlan.query.filter_by(name=args.name).first()
        if existing:
            print(f"Error: Plan with name '{args.name}' already exists (ID: {existing.id})")
            return
        
        plan = SubscriptionPlan(
            name=args.name,
            description=args.description,
            price=args.price,
            currency=args.currency or 'USD',
            has_trial=args.trial_days > 0 if args.trial_days else False,
            trial_days=args.trial_days or 0,
            is_active=True,
            display_order=args.order or 0
        )
        
        db.session.add(plan)
        db.session.commit()
        
        print(f"\n✓ Plan created successfully!")
        print(f"  ID: {plan.id}")
        print(f"  Name: {plan.name}")
        print(f"  Price: ${float(plan.price):.2f} {plan.currency}")
        if plan.has_trial:
            print(f"  Trial: {plan.trial_days} days")
        print(f"  Display Order: {plan.display_order}")

def update_plan(args):
    """Update an existing subscription plan."""
    with app.app_context():
        plan = SubscriptionPlan.query.get(args.id)
        if not plan:
            print(f"Error: Plan with ID {args.id} not found.")
            return
        
        if args.name:
            # Check if new name conflicts with another plan
            existing = SubscriptionPlan.query.filter_by(name=args.name).first()
            if existing and existing.id != plan.id:
                print(f"Error: Plan with name '{args.name}' already exists (ID: {existing.id})")
                return
            plan.name = args.name
        
        if args.description is not None:
            plan.description = args.description
        
        if args.price is not None:
            plan.price = args.price
        
        if args.currency:
            plan.currency = args.currency
        
        if args.trial_days is not None:
            plan.has_trial = args.trial_days > 0
            plan.trial_days = args.trial_days
        
        if args.active is not None:
            plan.is_active = args.active
        
        if args.order is not None:
            plan.display_order = args.order
        
        db.session.commit()
        
        print(f"\n✓ Plan updated successfully!")
        print(f"  ID: {plan.id}")
        print(f"  Name: {plan.name}")
        print(f"  Price: ${float(plan.price):.2f} {plan.currency}")
        if plan.has_trial:
            print(f"  Trial: {plan.trial_days} days")
        print(f"  Status: {'Active' if plan.is_active else 'Inactive'}")

def delete_plan(args):
    """Delete a subscription plan."""
    with app.app_context():
        plan = SubscriptionPlan.query.get(args.id)
        if not plan:
            print(f"Error: Plan with ID {args.id} not found.")
            return
        
        # Check if plan is being used
        subscribers_count = Subscriber.query.filter_by(plan_id=plan.id).count()
        if subscribers_count > 0:
            print(f"Error: Cannot delete plan '{plan.name}' - it is being used by {subscribers_count} subscriber(s).")
            print("  Please update or delete those subscribers first.")
            return
        
        if not args.force:
            confirmation = input(f"\n⚠️  Are you sure you want to delete plan '{plan.name}'? (yes/no): ")
            if confirmation.lower() != 'yes':
                print("Operation cancelled.")
                return
        
        plan_name = plan.name
        db.session.delete(plan)
        db.session.commit()
        
        print(f"\n✓ Plan '{plan_name}' deleted successfully!")

# ========== Discount Code Management Functions ==========

def list_codes(args):
    """List all discount codes."""
    with app.app_context():
        codes = DiscountCode.query.order_by(DiscountCode.created_at.desc()).all()
        
        if args.active_only:
            codes = [c for c in codes if c.is_active]
        
        if not codes:
            print("No discount codes found.")
            return
        
        table_data = []
        for code in codes:
            discount_display = f"{float(code.discount_value):.0f}%" if code.discount_type == 'percent' else f"${float(code.discount_value):.2f}"
            uses_display = f"{code.current_uses}/{code.max_uses}" if code.max_uses else f"{code.current_uses}/∞"
            status = "✓ Active" if code.is_active else "✗ Inactive"
            valid_until = format_date(code.valid_until) if code.valid_until else "No expiry"
            
            table_data.append([
                code.id,
                code.code,
                code.discount_type,
                discount_display,
                uses_display,
                status,
                valid_until,
                format_date(code.created_at)
            ])
        
        headers = ['ID', 'Code', 'Type', 'Value', 'Uses', 'Status', 'Valid Until', 'Created']
        print(f"\nTotal Codes: {len(table_data)}")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))

def create_code(args):
    """Create a new discount code."""
    with app.app_context():
        # Check if code already exists
        existing = DiscountCode.query.filter_by(code=args.code.upper()).first()
        if existing:
            print(f"Error: Discount code '{args.code.upper()}' already exists (ID: {existing.id})")
            return
        
        # Validate discount value
        if args.type == 'percent' and (args.value < 0 or args.value > 100):
            print("Error: Percentage discount must be between 0 and 100.")
            return
        
        if args.type == 'fixed' and args.value < 0:
            print("Error: Fixed discount cannot be negative.")
            return
        
        # Parse validity dates
        valid_from = None
        valid_until = None
        if args.valid_from:
            valid_from = datetime.fromisoformat(args.valid_from.replace('Z', '+00:00'))
        if args.valid_until:
            valid_until = datetime.fromisoformat(args.valid_until.replace('Z', '+00:00'))
        
        code = DiscountCode(
            code=args.code.upper(),
            description=args.description,
            discount_type=args.type,
            discount_value=args.value,
            max_uses=args.max_uses,
            valid_from=valid_from,
            valid_until=valid_until,
            is_active=True,
            applicable_plan_ids=args.plan_ids if args.plan_ids else None
        )
        
        db.session.add(code)
        db.session.commit()
        
        discount_display = f"{float(code.discount_value):.0f}%" if code.discount_type == 'percent' else f"${float(code.discount_value):.2f}"
        print(f"\n✓ Discount code created successfully!")
        print(f"  ID: {code.id}")
        print(f"  Code: {code.code}")
        print(f"  Type: {code.discount_type}")
        print(f"  Value: {discount_display}")
        if code.max_uses:
            print(f"  Max Uses: {code.max_uses}")
        if code.valid_until:
            print(f"  Valid Until: {format_date(code.valid_until)}")
        if code.applicable_plan_ids:
            print(f"  Applicable Plans: {code.applicable_plan_ids}")

def update_code(args):
    """Update an existing discount code."""
    with app.app_context():
        code = DiscountCode.query.get(args.id)
        if not code:
            print(f"Error: Discount code with ID {args.id} not found.")
            return
        
        if args.code:
            # Check if new code conflicts with another code
            existing = DiscountCode.query.filter_by(code=args.code.upper()).first()
            if existing and existing.id != code.id:
                print(f"Error: Discount code '{args.code.upper()}' already exists (ID: {existing.id})")
                return
            code.code = args.code.upper()
        
        if args.description is not None:
            code.description = args.description
        
        if args.type:
            code.discount_type = args.type
        
        if args.value is not None:
            # Validate discount value
            if code.discount_type == 'percent' and (args.value < 0 or args.value > 100):
                print("Error: Percentage discount must be between 0 and 100.")
                return
            if code.discount_type == 'fixed' and args.value < 0:
                print("Error: Fixed discount cannot be negative.")
                return
            code.discount_value = args.value
        
        if args.max_uses is not None:
            code.max_uses = args.max_uses
        
        if args.valid_from:
            code.valid_from = datetime.fromisoformat(args.valid_from.replace('Z', '+00:00'))
        
        if args.valid_until:
            code.valid_until = datetime.fromisoformat(args.valid_until.replace('Z', '+00:00'))
        
        if args.active is not None:
            code.is_active = args.active
        
        if args.plan_ids is not None:
            code.applicable_plan_ids = args.plan_ids if args.plan_ids else None
        
        db.session.commit()
        
        discount_display = f"{float(code.discount_value):.0f}%" if code.discount_type == 'percent' else f"${float(code.discount_value):.2f}"
        print(f"\n✓ Discount code updated successfully!")
        print(f"  ID: {code.id}")
        print(f"  Code: {code.code}")
        print(f"  Type: {code.discount_type}")
        print(f"  Value: {discount_display}")
        print(f"  Uses: {code.current_uses}/{code.max_uses if code.max_uses else '∞'}")
        print(f"  Status: {'Active' if code.is_active else 'Inactive'}")

def delete_code(args):
    """Delete a discount code."""
    with app.app_context():
        code = DiscountCode.query.get(args.id)
        if not code:
            print(f"Error: Discount code with ID {args.id} not found.")
            return
        
        if not args.force:
            confirmation = input(f"\n⚠️  Are you sure you want to delete discount code '{code.code}'? (yes/no): ")
            if confirmation.lower() != 'yes':
                print("Operation cancelled.")
                return
        
        code_name = code.code
        db.session.delete(code)
        db.session.commit()
        
        print(f"\n✓ Discount code '{code_name}' deleted successfully!")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Admin CLI for Subscription Service Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all subscribers
  python admin_cli.py list

  # List active subscribers only
  python admin_cli.py list --status active

  # Show subscriber details
  python admin_cli.py show 1

  # Send message to subscriber
  python admin_cli.py send 1 --message "Hello!"

  # Schedule a message
  python admin_cli.py schedule 1 --message "Reminder" --time "2024-01-15T10:00:00"

  # Update subscriber status
  python admin_cli.py update-status 1 --status active

  # View statistics
  python admin_cli.py stats

  # Export subscribers to CSV
  python admin_cli.py export --output subscribers.csv

  # List pending payments (includes Stripe, PayPal, and Crypto)
  python admin_cli.py pending-payments

  # Approve a pending payment (works for Stripe, PayPal, Crypto)
  # If webhook fails, you can manually approve Stripe/PayPal payments
  python admin_cli.py approve-payment 1 --notes "Payment verified"

  # Reject a pending payment
  python admin_cli.py reject-payment 1 --reason "Invalid transaction"
  # Or without reason (uses default)
  python admin_cli.py reject-payment 1
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List subscribers
    list_parser = subparsers.add_parser('list', help='List all subscribers')
    list_parser.add_argument('--status', choices=['active', 'pending', 'cancelled', 'expired', 'inactive'],
                            help='Filter by status')
    list_parser.set_defaults(func=list_subscribers)
    
    # Show subscriber
    show_parser = subparsers.add_parser('show', help='Show subscriber details')
    show_parser.add_argument('id', type=int, help='Subscriber ID')
    show_parser.set_defaults(func=show_subscriber)
    
    # Send message
    send_parser = subparsers.add_parser('send', help='Send message to subscriber')
    send_parser.add_argument('id', type=int, help='Subscriber ID')
    send_parser.add_argument('--message', '-m', required=True, help='Message text')
    send_parser.add_argument('--confirm', '-y', action='store_true', help='Skip confirmation')
    send_parser.set_defaults(func=send_message)
    
    # Schedule message
    schedule_parser = subparsers.add_parser('schedule', help='Schedule a message')
    schedule_parser.add_argument('id', type=int, help='Subscriber ID')
    schedule_parser.add_argument('--message', '-m', required=True, help='Message text')
    schedule_parser.add_argument('--time', '-t', help='Scheduled time (ISO format: YYYY-MM-DDTHH:MM:SS)')
    schedule_parser.set_defaults(func=schedule_message)
    
    # Update status
    status_parser = subparsers.add_parser('update-status', help='Update subscriber status')
    status_parser.add_argument('id', type=int, help='Subscriber ID')
    status_parser.add_argument('--status', required=True, 
                             choices=['active', 'pending', 'cancelled', 'expired', 'inactive'],
                             help='New status')
    status_parser.set_defaults(func=update_status)
    
    # Delete subscriber
    delete_parser = subparsers.add_parser('delete', help='Delete a subscriber')
    delete_parser.add_argument('id', type=int, help='Subscriber ID')
    delete_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    delete_parser.set_defaults(func=delete_subscriber)
    
    # List messages
    messages_parser = subparsers.add_parser('messages', help='List scheduled messages')
    messages_parser.add_argument('--sent', action='store_true', help='Show only sent messages')
    messages_parser.add_argument('--pending', action='store_true', help='Show only pending messages')
    messages_parser.add_argument('--subscriber-id', type=int, help='Filter by subscriber ID')
    messages_parser.set_defaults(func=list_messages)
    
    # Statistics
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.set_defaults(func=stats)
    
    # Export
    export_parser = subparsers.add_parser('export', help='Export subscribers to CSV')
    export_parser.add_argument('--output', '-o', help='Output filename')
    export_parser.set_defaults(func=export_subscribers)
    
    # List pending payments
    pending_parser = subparsers.add_parser('pending-payments', help='List all pending payments')
    pending_parser.set_defaults(func=list_pending_payments)
    
    # Approve payment
    approve_parser = subparsers.add_parser('approve-payment', help='Approve a pending payment')
    approve_parser.add_argument('id', type=int, help='Payment ID (DepositApproval ID or Subscriber ID)')
    approve_parser.add_argument('--notes', help='Admin notes for approval')
    approve_parser.add_argument('--admin', help='Admin identifier')
    approve_parser.set_defaults(func=approve_payment)
    
    # Reject payment
    reject_parser = subparsers.add_parser('reject-payment', help='Reject a pending payment')
    reject_parser.add_argument('id', type=int, help='Payment ID (DepositApproval ID or Subscriber ID)')
    reject_parser.add_argument('--reason', help='Reason for rejection (default: Payment rejected by admin)')
    reject_parser.add_argument('--admin', help='Admin identifier')
    reject_parser.set_defaults(func=reject_payment)
    
    # ========== Plan Management Commands ==========
    
    # Plans subparser
    plans_parser = subparsers.add_parser('plans', help='Manage subscription plans')
    plans_subparsers = plans_parser.add_subparsers(dest='plan_command', help='Plan commands')
    
    # List plans
    plans_list_parser = plans_subparsers.add_parser('list', help='List all plans')
    plans_list_parser.set_defaults(func=list_plans)
    
    # Create plan
    plans_create_parser = plans_subparsers.add_parser('create', help='Create a new plan')
    plans_create_parser.add_argument('--name', required=True, help='Plan name')
    plans_create_parser.add_argument('--description', help='Plan description')
    plans_create_parser.add_argument('--price', type=float, required=True, help='Monthly price')
    plans_create_parser.add_argument('--currency', default='USD', help='Currency (default: USD)')
    plans_create_parser.add_argument('--trial-days', type=int, default=0, help='Trial period in days (default: 0)')
    plans_create_parser.add_argument('--order', type=int, default=0, help='Display order (default: 0)')
    plans_create_parser.set_defaults(func=create_plan)
    
    # Update plan
    plans_update_parser = plans_subparsers.add_parser('update', help='Update a plan')
    plans_update_parser.add_argument('id', type=int, help='Plan ID')
    plans_update_parser.add_argument('--name', help='Plan name')
    plans_update_parser.add_argument('--description', help='Plan description')
    plans_update_parser.add_argument('--price', type=float, help='Monthly price')
    plans_update_parser.add_argument('--currency', help='Currency')
    plans_update_parser.add_argument('--trial-days', type=int, help='Trial period in days')
    plans_update_parser.add_argument('--active', type=bool, help='Is active (True/False)')
    plans_update_parser.add_argument('--order', type=int, help='Display order')
    plans_update_parser.set_defaults(func=update_plan)
    
    # Delete plan
    plans_delete_parser = plans_subparsers.add_parser('delete', help='Delete a plan')
    plans_delete_parser.add_argument('id', type=int, help='Plan ID')
    plans_delete_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    plans_delete_parser.set_defaults(func=delete_plan)
    
    # ========== Discount Code Management Commands ==========
    
    # Codes subparser
    codes_parser = subparsers.add_parser('codes', help='Manage discount codes')
    codes_subparsers = codes_parser.add_subparsers(dest='code_command', help='Code commands')
    
    # List codes
    codes_list_parser = codes_subparsers.add_parser('list', help='List all discount codes')
    codes_list_parser.add_argument('--active-only', action='store_true', help='Show only active codes')
    codes_list_parser.set_defaults(func=list_codes)
    
    # Create code
    codes_create_parser = codes_subparsers.add_parser('create', help='Create a new discount code')
    codes_create_parser.add_argument('--code', required=True, help='Discount code (e.g., SAVE50)')
    codes_create_parser.add_argument('--description', help='Code description')
    codes_create_parser.add_argument('--type', choices=['percent', 'fixed'], required=True, help='Discount type')
    codes_create_parser.add_argument('--value', type=float, required=True, help='Discount value (percentage 0-100 or fixed amount)')
    codes_create_parser.add_argument('--max-uses', type=int, help='Maximum uses (default: unlimited)')
    codes_create_parser.add_argument('--valid-from', help='Valid from date (ISO format: YYYY-MM-DDTHH:MM:SS)')
    codes_create_parser.add_argument('--valid-until', help='Valid until date (ISO format: YYYY-MM-DDTHH:MM:SS)')
    codes_create_parser.add_argument('--plan-ids', help='Applicable plan IDs (comma-separated, default: all plans)')
    codes_create_parser.set_defaults(func=create_code)
    
    # Update code
    codes_update_parser = codes_subparsers.add_parser('update', help='Update a discount code')
    codes_update_parser.add_argument('id', type=int, help='Code ID')
    codes_update_parser.add_argument('--code', help='Discount code')
    codes_update_parser.add_argument('--description', help='Code description')
    codes_update_parser.add_argument('--type', choices=['percent', 'fixed'], help='Discount type')
    codes_update_parser.add_argument('--value', type=float, help='Discount value')
    codes_update_parser.add_argument('--max-uses', type=int, help='Maximum uses')
    codes_update_parser.add_argument('--valid-from', help='Valid from date (ISO format)')
    codes_update_parser.add_argument('--valid-until', help='Valid until date (ISO format)')
    codes_update_parser.add_argument('--active', type=bool, help='Is active (True/False)')
    codes_update_parser.add_argument('--plan-ids', help='Applicable plan IDs (comma-separated)')
    codes_update_parser.set_defaults(func=update_code)
    
    # Delete code
    codes_delete_parser = codes_subparsers.add_parser('delete', help='Delete a discount code')
    codes_delete_parser.add_argument('id', type=int, help='Code ID')
    codes_delete_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    codes_delete_parser.set_defaults(func=delete_code)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Handle subcommands for plans and codes
    if args.command == 'plans' and hasattr(args, 'plan_command'):
        if not args.plan_command:
            plans_parser.print_help()
            return
        # The func is already set on the subparser
    elif args.command == 'codes' and hasattr(args, 'code_command'):
        if not args.code_command:
            codes_parser.print_help()
            return
        # The func is already set on the subparser
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

