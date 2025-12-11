from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from models import db, Subscriber, ScheduledMessage, DepositApproval
from email_sms_gateways import get_sms_email, list_available_carriers
from subscription_manager import create_subscription as create_stripe_subscription, cancel_subscription as cancel_stripe_subscription, handle_stripe_webhook
from paypal_manager import create_paypal_subscription, execute_paypal_agreement, cancel_paypal_subscription, handle_paypal_webhook
from crypto_manager import create_crypto_checkout, create_manual_crypto_subscription, verify_manual_crypto_payment, handle_coinbase_webhook, get_crypto_wallet_addresses, get_available_crypto_currencies
from sms_sender import send_sms_to_subscriber
from scheduler import schedule_message, start_scheduler
from telegram_bot import setup_telegram_bot, send_telegram_notification
from admin_routes import admin_bp
import stripe
from datetime import datetime, timedelta, timezone
import threading
import os

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Register admin blueprint
app.register_blueprint(admin_bp)

# Initialize database
db.init_app(app)

# Initialize Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

with app.app_context():
    db.create_all()

# API Routes

@app.route('/', methods=['GET'])
def index():
    """Root endpoint - API information."""
    return jsonify({
        'message': 'Subscription Service Bot API',
        'version': '1.0',
        'endpoints': {
            'health': '/api/health',
            'carriers': '/api/carriers',
            'subscribe': '/api/subscribe (POST)',
            'subscribers': '/api/subscribers (GET)',
            'stripe_webhook': '/api/stripe-webhook (POST)',
            'paypal_webhook': '/api/paypal-webhook (POST)',
            'crypto_webhook': '/api/crypto-webhook (POST)',
            'admin_panel': '/admin (Web-based admin interface)'
        },
        'telegram_bot': 'Available' if Config.TELEGRAM_BOT_TOKEN else 'Not configured',
        'admin_panel': 'Available at /admin'
    })

@app.route('/api', methods=['GET'])
def api_info():
    """API information endpoint."""
    return jsonify({
        'message': 'Subscription Service Bot API',
        'version': '1.0',
        'documentation': 'See README.md for API documentation'
    })

@app.route('/api/carriers', methods=['GET'])
def get_carriers():
    """Get list of available carriers."""
    from email_sms_gateways import EMAIL_SMS_GATEWAYS
    return jsonify({
        'carriers': list_available_carriers(),
        'gateways': {k: f"[10-digit-number]@{v}" for k, v in EMAIL_SMS_GATEWAYS.items()}
    })

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    """Create a new subscriber and subscription."""
    data = request.get_json()
    
    required_fields = ['phone_number', 'carrier']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Generate SMS email address
        sms_email = get_sms_email(data['phone_number'], data['carrier'])
        
        # Check if subscriber already exists
        existing = Subscriber.query.filter_by(phone_number=data['phone_number']).first()
        if existing:
            return jsonify({
                'error': 'Subscriber already exists',
                'subscriber': existing.to_dict()
            }), 400
        
        # Get payment method (default to stripe)
        payment_method = data.get('payment_method', 'stripe').lower()
        
        # Create subscriber
        subscriber = Subscriber(
            phone_number=data['phone_number'],
            carrier=data['carrier'],
            email=data.get('email'),
            name=data.get('name'),
            sms_email=sms_email,
            subscription_status='inactive',
            payment_method=payment_method
        )
        db.session.add(subscriber)
        db.session.commit()
        
        # Create subscription based on payment method
        try:
            if payment_method == 'stripe':
                # Create Stripe customer first (if not exists)
                if not subscriber.stripe_customer_id:
                    from subscription_manager import create_stripe_customer
                    create_stripe_customer(subscriber)
                
                # Create Stripe Checkout session for payment collection
                # This will automatically create the subscription when payment is collected
                checkout_url = None
                try:
                    checkout_session = stripe.checkout.Session.create(
                        customer=subscriber.stripe_customer_id,
                        payment_method_types=['card'],
                        line_items=[{
                            'price_data': {
                                'currency': 'usd',
                                'product_data': {'name': 'Monthly Subscription'},
                                'unit_amount': int(Config.MONTHLY_PRICE * 100),
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
                    checkout_url = checkout_session.url
                    
                    # Update subscriber status to pending
                    subscriber.subscription_status = 'pending'
                    db.session.commit()
                except Exception as e:
                    return jsonify({'error': f'Failed to create checkout session: {str(e)}'}), 500
                
                return jsonify({
                    'message': 'Subscriber created successfully. Please complete payment.',
                    'subscriber': subscriber.to_dict(),
                    'checkout_url': checkout_url,
                    'payment_method': 'stripe'
                }), 201
            
            elif payment_method == 'paypal':
                subscription = create_paypal_subscription(subscriber)
                return jsonify({
                    'message': 'Subscriber created successfully',
                    'subscriber': subscriber.to_dict(),
                    'subscription': {
                        'id': subscription['id'],
                        'status': subscription['status'],
                        'payment_method': 'paypal',
                        'approval_url': subscription['approval_url']
                    }
                }), 201
            
            elif payment_method == 'crypto':
                # Check if using Coinbase Commerce or manual
                crypto_type = data.get('crypto_type', 'coinbase')  # coinbase or manual
                currency = data.get('currency', 'BTC')
                
                if crypto_type == 'coinbase':
                    checkout = create_crypto_checkout(subscriber)
                    return jsonify({
                        'message': 'Subscriber created successfully',
                        'subscriber': subscriber.to_dict(),
                        'subscription': {
                            'id': checkout['id'],
                            'status': 'pending',
                            'payment_method': 'crypto',
                            'checkout_url': checkout['hosted_url'],
                            'checkout_code': checkout['code']
                        }
                    }), 201
                else:
                    # Manual crypto payment
                    try:
                        payment_info = create_manual_crypto_subscription(subscriber, currency)
                        return jsonify({
                            'message': 'Subscriber created successfully',
                            'subscriber': subscriber.to_dict(),
                            'subscription': {
                                'status': 'pending',
                                'payment_method': 'crypto',
                                'payment_info': payment_info
                            }
                        }), 201
                    except ValueError as e:
                        # Handle wallet address not configured error
                        available_currencies = get_available_crypto_currencies()
                        coinbase_available = Config.COINBASE_COMMERCE_API_KEY is not None
                        
                        error_response = {
                            'error': str(e),
                            'available_currencies': available_currencies,
                            'coinbase_available': coinbase_available
                        }
                        
                        if coinbase_available:
                            error_response['suggestion'] = 'Use crypto_type=coinbase for automatic crypto payments'
                        
                        return jsonify(error_response), 400
            
            else:
                return jsonify({'error': f'Unsupported payment method: {payment_method}'}), 400
                
        except Exception as e:
            return jsonify({
                'error': f'Failed to create subscription: {str(e)}',
                'subscriber': subscriber.to_dict()
            }), 500
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscribers', methods=['GET'])
def get_subscribers():
    """Get all subscribers."""
    subscribers = Subscriber.query.all()
    return jsonify({
        'subscribers': [s.to_dict() for s in subscribers]
    })

@app.route('/api/subscribers/<int:subscriber_id>', methods=['GET'])
def get_subscriber(subscriber_id):
    """Get a specific subscriber."""
    subscriber = Subscriber.query.get_or_404(subscriber_id)
    return jsonify(subscriber.to_dict())

@app.route('/api/subscribers/<int:subscriber_id>', methods=['DELETE'])
def delete_subscriber(subscriber_id):
    """Cancel subscription and delete subscriber."""
    subscriber = Subscriber.query.get_or_404(subscriber_id)
    
    # Cancel subscription based on payment method
    try:
        if subscriber.payment_method == 'stripe' and subscriber.stripe_subscription_id:
            cancel_stripe_subscription(subscriber)
        elif subscriber.payment_method == 'paypal' and subscriber.paypal_subscription_id:
            cancel_paypal_subscription(subscriber)
        # Crypto subscriptions are one-time payments, no cancellation needed
    except:
        pass
    
    db.session.delete(subscriber)
    db.session.commit()
    
    return jsonify({'message': 'Subscriber deleted successfully'})

@app.route('/api/subscribers/<int:subscriber_id>/send-sms', methods=['POST'])
def send_sms(subscriber_id):
    """Send an immediate SMS to a subscriber."""
    subscriber = Subscriber.query.get_or_404(subscriber_id)
    data = request.get_json()
    
    if 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400
    
    # Check if subscriber is active
    if subscriber.subscription_status != 'active':
        return jsonify({'error': 'Subscriber is not active'}), 400
    
    success = send_sms_to_subscriber(subscriber, data['message'])
    
    if success:
        return jsonify({'message': 'SMS sent successfully'})
    else:
        return jsonify({'error': 'Failed to send SMS'}), 500

@app.route('/api/subscribers/<int:subscriber_id>/schedule-message', methods=['POST'])
def schedule_sms(subscriber_id):
    """Schedule a message for a subscriber."""
    subscriber = Subscriber.query.get_or_404(subscriber_id)
    data = request.get_json()
    
    required_fields = ['message', 'scheduled_time']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        scheduled_input = datetime.fromisoformat(data['scheduled_time'].replace('Z', '+00:00'))
        timezone_offset = subscriber.timezone_offset_minutes or 0
        timezone_label = subscriber.timezone_label or 'UTC'

        def format_offset(minutes: int) -> str:
            sign = '+' if minutes >= 0 else '-'
            minutes_abs = abs(minutes)
            hours = minutes_abs // 60
            mins = minutes_abs % 60
            return f"UTC{sign}{hours:02d}:{mins:02d}"

        if scheduled_input.tzinfo is not None:
            utc_time = scheduled_input.astimezone(timezone.utc)
            local_display = (utc_time + timedelta(minutes=timezone_offset)).replace(tzinfo=None)
            scheduled_utc = utc_time.replace(tzinfo=None)
        else:
            local_display = scheduled_input
            scheduled_utc = scheduled_input - timedelta(minutes=timezone_offset)
        
        # Create scheduled message
        scheduled_msg = schedule_message(
            subscriber_id,
            data['message'],
            scheduled_utc,
            timezone_offset_minutes=timezone_offset,
            timezone_label=timezone_label
        )
        
        timezone_display = format_offset(timezone_offset)
        if timezone_label and timezone_label != 'UTC':
            timezone_display = f"{timezone_label} ({timezone_display})"
        
        return jsonify({
            'message': f'Message scheduled successfully for {local_display.strftime("%Y-%m-%d %H:%M:%S")} {timezone_display}',
            'scheduled_message': {
                'id': scheduled_msg.id,
                'subscriber_id': scheduled_msg.subscriber_id,
                'message': scheduled_msg.message,
                'scheduled_time': scheduled_msg.scheduled_time.isoformat() if scheduled_msg.scheduled_time else None,
                'scheduled_time_local': local_display.isoformat(),
                'timezone_offset_minutes': timezone_offset,
                'timezone_label': timezone_label,
                'sent': scheduled_msg.sent
            }
        }), 201
    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verify webhook signature if secret is configured
        if Config.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
            )
        else:
            # For development, parse without verification
            import json
            event = json.loads(payload)
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    try:
        event_type = event.get('type') if isinstance(event, dict) else event.type
        
        # Handle checkout.session.completed (when payment is collected via Checkout)
        if event_type == 'checkout.session.completed':
            session = event['data']['object'] if isinstance(event, dict) else event.data.object
            subscriber_id = session.metadata.get('subscriber_id')
            
            if subscriber_id:
                subscriber = Subscriber.query.get(subscriber_id)
                if subscriber:
                    # Get subscription from checkout session
                    subscription_id = session.subscription
                    if subscription_id:
                        # Retrieve subscription details
                        subscription = stripe.Subscription.retrieve(subscription_id)
                        
                        # Update subscriber with subscription info
                        subscriber.stripe_subscription_id = subscription.id
                        subscriber.subscription_status = subscription.status
                        
                        # Create or update subscription record
                        from models import Subscription
                        from datetime import datetime
                        sub_record = Subscription.query.filter_by(
                            subscriber_id=subscriber.id,
                            payment_method='stripe'
                        ).first()
                        
                        if not sub_record:
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
                        else:
                            sub_record.status = subscription.status
                            sub_record.current_period_start = datetime.fromtimestamp(subscription.current_period_start)
                            sub_record.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
                        
                        db.session.commit()
        
        # Handle other subscription events
        from subscription_manager import handle_stripe_webhook
        result = handle_stripe_webhook(event)
        return jsonify(result)
    except Exception as e:
        import logging
        logging.error(f"Error processing Stripe webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/paypal/approve', methods=['POST'])
def paypal_approve():
    """Execute PayPal billing agreement after user approval."""
    data = request.get_json()
    
    required_fields = ['subscriber_id', 'payer_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    subscriber = Subscriber.query.get_or_404(data['subscriber_id'])
    
    try:
        agreement = execute_paypal_agreement(subscriber, data['payer_id'])
        return jsonify({
            'message': 'PayPal subscription activated successfully',
            'subscriber': subscriber.to_dict(),
            'subscription': {
                'id': agreement.id,
                'status': agreement.state
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/paypal-webhook', methods=['POST'])
def paypal_webhook():
    """Handle PayPal webhook events."""
    event_type = request.headers.get('PAYPAL-TRANSMISSION-SIG')
    resource = request.get_json()
    
    # PayPal webhook verification would go here
    # For now, process the event
    event_type = request.json.get('event_type')
    resource = request.json.get('resource', {})
    
    try:
        result = handle_paypal_webhook(event_type, resource)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crypto/wallets', methods=['GET'])
def get_crypto_wallets():
    """Get cryptocurrency wallet addresses for manual payment."""
    wallets = get_crypto_wallet_addresses()
    return jsonify({
        'wallets': wallets,
        'monthly_price': Config.MONTHLY_PRICE
    })

@app.route('/api/crypto/verify', methods=['POST'])
def verify_crypto_payment():
    """Manually verify and activate crypto subscription."""
    data = request.get_json()
    
    required_fields = ['subscriber_id', 'transaction_hash']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    subscriber = Subscriber.query.get_or_404(data['subscriber_id'])
    
    try:
        subscription = verify_manual_crypto_payment(subscriber, data['transaction_hash'])
        return jsonify({
            'message': 'Cryptocurrency payment verified and subscription activated',
            'subscriber': subscriber.to_dict(),
            'subscription': {
                'id': subscription.id,
                'status': subscription.status
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crypto-webhook', methods=['POST'])
def crypto_webhook():
    """Handle Coinbase Commerce webhook events."""
    try:
        result = handle_coinbase_webhook()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscribe/success', methods=['GET'])
def subscription_success():
    """Handle successful subscription payment."""
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            subscriber_id = session.metadata.get('subscriber_id')
            if subscriber_id:
                subscriber = Subscriber.query.get(subscriber_id)
                if subscriber:
                    # Get subscription from checkout session
                    subscription_id = session.subscription
                    if subscription_id:
                        # Retrieve subscription details
                        subscription = stripe.Subscription.retrieve(subscription_id)
                        
                        # Update subscriber with subscription info
                        subscriber.stripe_subscription_id = subscription.id
                        subscriber.subscription_status = subscription.status
                        
                        # Create or update subscription record
                        from models import Subscription
                        from datetime import datetime
                        sub_record = Subscription.query.filter_by(
                            subscriber_id=subscriber.id,
                            payment_method='stripe'
                        ).first()
                        
                        if not sub_record:
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
                        else:
                            sub_record.status = subscription.status
                            sub_record.current_period_start = datetime.fromtimestamp(subscription.current_period_start)
                            sub_record.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
                        
                        db.session.commit()
                    
                    return jsonify({
                        'message': 'Subscription activated successfully!',
                        'subscriber': subscriber.to_dict()
                    })
        except Exception as e:
            import logging
            logging.error(f"Error processing subscription success: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    return jsonify({'message': 'Subscription payment completed'})

@app.route('/api/subscribe/cancel', methods=['GET'])
def subscription_cancel():
    """Handle canceled subscription payment."""
    return jsonify({'message': 'Subscription payment canceled'})

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})

# Global lock to prevent multiple bot instances
_bot_running = False
_bot_lock = threading.Lock()

def run_telegram_bot(telegram_app):
    """Run Telegram bot in a separate thread."""
    global _bot_running
    
    try:
        if telegram_app:
            # Check if bot is already running
            with _bot_lock:
                if _bot_running:
                    print("[WARNING] Bot is already running, skipping...")
                    return
                _bot_running = True
            
            # Create event loop for this thread (required for async operations in threads)
            import asyncio
            from telegram.error import Conflict
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # For python-telegram-bot v21, we need to use async context properly
            async def run_bot():
                try:
                    # Delete webhook first to ensure no conflicts
                    try:
                        await telegram_app.bot.delete_webhook(drop_pending_updates=True)
                    except:
                        pass
                    
                    # Initialize and start the application
                    await telegram_app.initialize()
                    await telegram_app.start()
                    
                    # Start polling with retry logic for Conflict errors
                    retry_count = 0
                    max_retries = 3
                    
                    while retry_count < max_retries:
                        try:
                            await telegram_app.updater.start_polling(
                                drop_pending_updates=True,
                                allowed_updates=None
                            )
                            print("[OK] Telegram bot polling started successfully!")
                            break
                        except Conflict as e:
                            retry_count += 1
                            if retry_count < max_retries:
                                print(f"[WARNING] Conflict error (another instance may be running), retrying in 3 seconds... ({retry_count}/{max_retries})")
                                await asyncio.sleep(3)
                                # Delete webhook again
                                try:
                                    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
                                    await asyncio.sleep(1)
                                except:
                                    pass
                            else:
                                # If conflicts persist, log but don't crash - bot might still work
                                import logging
                                logging.warning(f"Bot conflict after {max_retries} retries. Another instance may be running. Bot may still work.")
                                # Don't raise - let it continue, sometimes it works despite conflicts
                                break
                    
                    # Keep the event loop running
                    stop_event = asyncio.Event()
                    await stop_event.wait()  # Wait forever
                    
                except Conflict as e:
                    import logging
                    logging.error(f"Bot conflict error: {e}. Make sure only one bot instance is running.")
                except Exception as e:
                    import logging
                    logging.error(f"Error in bot polling: {e}", exc_info=True)
                finally:
                    # Cleanup
                    try:
                        await telegram_app.updater.stop()
                        await telegram_app.stop()
                        await telegram_app.shutdown()
                    except:
                        pass
                    finally:
                        with _bot_lock:
                            _bot_running = False
            
            # Run the async function
            try:
                loop.run_until_complete(run_bot())
            except KeyboardInterrupt:
                pass
            finally:
                loop.close()
                with _bot_lock:
                    _bot_running = False
                
    except Exception as e:
        import logging
        logging.error(f"Telegram bot error: {e}", exc_info=True)
        with _bot_lock:
            _bot_running = False

if __name__ == '__main__':
    # Start scheduler
    start_scheduler(app)
    
    # Create Telegram bot application in main thread (before threading)
    # IMPORTANT: Only start bot once to avoid conflicts
    if Config.TELEGRAM_BOT_TOKEN:
        # Delete any existing webhook first
        try:
            import requests
            delete_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/deleteWebhook"
            requests.get(delete_url, params={"drop_pending_updates": True}, timeout=5)
            print("[OK] Cleared any existing webhooks")
        except:
            pass
        
        telegram_app = setup_telegram_bot()
        if telegram_app:
            # Start Telegram bot in background thread
            telegram_thread = threading.Thread(target=run_telegram_bot, args=(telegram_app,), daemon=True)
            telegram_thread.start()
            print("[OK] Telegram bot thread started!")
        else:
            print("[WARNING] Telegram bot setup failed, continuing without bot...")
    
    # Run app - disable reloader to prevent multiple bot instances
    # Use PORT from environment (Railway provides this) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port, use_reloader=False)

