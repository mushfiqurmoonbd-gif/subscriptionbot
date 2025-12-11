"""
Group Message Scheduler
Schedules recurring messages (morning, noon, evening) for service groups
with timezone matching support based on subscriber preferences
"""
from datetime import datetime, timedelta, time
from models import db, Subscriber, ScheduledMessage, ServiceGroup
from scheduler import schedule_message
import json

def schedule_group_messages(group_id, message_type='morning', message_text=None, date=None):
    """
    Schedule messages for all active subscribers in a group.
    
    Args:
        group_id: Service group ID
        message_type: 'morning', 'noon', or 'evening'
        message_text: Message text to send (if None, uses default from group)
        date: Date to schedule (datetime.date, defaults to today)
    
    Returns:
        dict with scheduling results
    """
    with db.session.begin():
        group = ServiceGroup.query.get(group_id)
        if not group:
            return {'error': 'Group not found', 'scheduled': 0}
        
        # Get scheduled times from group
        scheduled_times = {}
        if group.scheduled_times:
            try:
                scheduled_times = json.loads(group.scheduled_times)
            except:
                pass
        
        # Get time for this message type
        time_str = scheduled_times.get(message_type, '08:00')  # Default 8 AM
        hour, minute = map(int, time_str.split(':'))
        
        # Get all active subscribers in this group
        subscribers = Subscriber.query.filter_by(
            group_id=group_id,
            subscription_status='active'
        ).all()
        
        if date is None:
            date = datetime.utcnow().date()
        
        scheduled_count = 0
        timezone_matched_count = 0
        non_timezone_matched_count = 0
        
        for subscriber in subscribers:
            # Use provided message or default
            final_message = message_text or f"Good {message_type}! 🌅" if message_type == 'morning' else f"Good {message_type}! ☀️" if message_type == 'noon' else f"Good {message_type}! 🌆"
            
            # Check if subscriber wants timezone matching
            use_timezone = subscriber.use_timezone_matching and subscriber.message_delivery_preference == 'scheduled_timezone'
            
            if use_timezone:
                # Calculate UTC time based on subscriber's timezone
                subscriber_local_time = datetime.combine(date, time(hour, minute))
                # Convert to UTC by subtracting timezone offset
                timezone_offset = subscriber.timezone_offset_minutes or 0
                utc_time = subscriber_local_time - timedelta(minutes=timezone_offset)
                timezone_matched_count += 1
            else:
                # Use same UTC time for everyone (not timezone-matched)
                # Schedule at the specified time in UTC
                utc_time = datetime.combine(date, time(hour, minute))
                non_timezone_matched_count += 1
            
            # Create scheduled message
            scheduled_msg = ScheduledMessage(
                subscriber_id=subscriber.id,
                message=final_message,
                scheduled_time=utc_time,
                timezone_offset_minutes=subscriber.timezone_offset_minutes or 0,
                timezone_label=subscriber.timezone_label or 'UTC'
            )
            
            db.session.add(scheduled_msg)
            scheduled_count += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'scheduled': scheduled_count,
            'timezone_matched': timezone_matched_count,
            'non_timezone_matched': non_timezone_matched_count,
            'message_type': message_type,
            'date': date.isoformat()
        }

def schedule_daily_group_messages(group_id, date=None):
    """
    Schedule all three daily messages (morning, noon, evening) for a group.
    
    Args:
        group_id: Service group ID
        date: Date to schedule (defaults to today)
    
    Returns:
        dict with results for all three message types
    """
    results = {}
    
    for msg_type in ['morning', 'noon', 'evening']:
        results[msg_type] = schedule_group_messages(group_id, msg_type, date=date)
    
    return results

def schedule_weekly_group_messages(group_id, start_date=None):
    """
    Schedule daily messages for a week.
    
    Args:
        group_id: Service group ID
        start_date: Starting date (defaults to today)
    
    Returns:
        dict with results for each day
    """
    if start_date is None:
        start_date = datetime.utcnow().date()
    
    results = {}
    
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        day_results = schedule_daily_group_messages(group_id, date=current_date)
        results[current_date.isoformat()] = day_results
    
    return results

