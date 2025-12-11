from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
from models import db, Subscriber, ScheduledMessage
from sms_sender import send_sms_to_subscriber

scheduler = BackgroundScheduler()

def send_pending_messages():
    """Check for and send any pending scheduled messages."""
    with scheduler.app.app_context():
        now = datetime.utcnow()
        pending_messages = ScheduledMessage.query.filter(
            ScheduledMessage.sent == False,
            ScheduledMessage.scheduled_time <= now
        ).all()
        
        for msg in pending_messages:
            subscriber = msg.subscriber
            
            # Only send to active subscribers
            if subscriber.subscription_status == 'active':
                success = send_sms_to_subscriber(subscriber, msg.message)
                if success:
                    msg.sent = True
                    msg.sent_at = datetime.utcnow()
                    db.session.commit()

def schedule_message(subscriber_id, message, scheduled_time, timezone_offset_minutes=0, timezone_label='UTC'):
    """
    Schedule a message for a subscriber.
    
    Args:
        subscriber_id: Subscriber ID
        message: Message text
        scheduled_time: datetime object for when to send (UTC or timezone-aware)
        timezone_offset_minutes: Minutes offset from UTC for recipient's local time
        timezone_label: Human-readable label for the timezone (e.g., 'UTC+5')
    
    Returns:
        ScheduledMessage instance
    """
    if scheduled_time.tzinfo is not None:
        scheduled_time = scheduled_time.astimezone(timezone.utc).replace(tzinfo=None)
    
    scheduled_msg = ScheduledMessage(
        subscriber_id=subscriber_id,
        message=message,
        scheduled_time=scheduled_time,
        timezone_offset_minutes=timezone_offset_minutes,
        timezone_label=timezone_label
    )
    db.session.add(scheduled_msg)
    db.session.commit()
    return scheduled_msg

def start_scheduler(app):
    """Start the scheduler with the Flask app context."""
    scheduler.app = app
    
    # Check for pending messages every minute
    scheduler.add_job(
        func=send_pending_messages,
        trigger=CronTrigger(second=0),  # Run at the start of every minute
        id='send_pending_messages',
        name='Send pending scheduled messages',
        replace_existing=True
    )
    
    scheduler.start()
    return scheduler

def stop_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()

