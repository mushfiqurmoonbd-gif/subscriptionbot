# Timezone Matching Guide for Motivational Group

## Overview
Your motivational group can send messages at morning (8 AM), noon (12 PM), and evening (6 PM). Users can choose whether they want these times matched to their timezone or not.

## How It Works

### User Choice During Subscription

When users subscribe, they select their **delivery preference**:

1. **📨 On-Demand**: Request messages when they want
2. **⏰ Scheduled**: Admin sends at scheduled times (NOT timezone-matched)
   - All users get messages at the same UTC time
   - Example: If scheduled for 8 AM UTC, everyone gets it at 8 AM UTC (which is different local times)
   
3. **🌍 Scheduled + Timezone Match**: Messages matched to user's timezone
   - Each user gets messages at the specified time in THEIR timezone
   - Example: If scheduled for 8 AM, user in EST gets it at 8 AM EST, user in PST gets it at 8 AM PST

### Example Scenario

**Group Settings:**
- Morning: 8:00 AM
- Noon: 12:00 PM  
- Evening: 6:00 PM

**Subscribers:**
- User A (New York, UTC-5): Chooses "Scheduled + Timezone Match"
- User B (Los Angeles, UTC-8): Chooses "Scheduled + Timezone Match"
- User C (London, UTC+0): Chooses "Scheduled" (no timezone matching)

**What Happens:**

**Morning Message (8 AM):**
- User A: Receives at 8:00 AM EST (1:00 PM UTC)
- User B: Receives at 8:00 AM PST (4:00 PM UTC)
- User C: Receives at 8:00 AM UTC (same for everyone without matching)

**Noon Message (12 PM):**
- User A: Receives at 12:00 PM EST (5:00 PM UTC)
- User B: Receives at 12:00 PM PST (8:00 PM UTC)
- User C: Receives at 12:00 PM UTC

**Evening Message (6 PM):**
- User A: Receives at 6:00 PM EST (11:00 PM UTC)
- User B: Receives at 6:00 PM PST (2:00 AM next day UTC)
- User C: Receives at 6:00 PM UTC

## How to Schedule Group Messages

### Option 1: Using Python Script

```python
from group_message_scheduler import schedule_daily_group_messages

# Schedule all three messages (morning, noon, evening) for today
results = schedule_daily_group_messages(group_id=1)

# Schedule for a specific date
from datetime import date
results = schedule_daily_group_messages(group_id=1, date=date(2024, 1, 15))

# Schedule only morning messages
from group_message_scheduler import schedule_group_messages
results = schedule_group_messages(group_id=1, message_type='morning')
```

### Option 2: Using Admin API

```bash
# Schedule all daily messages
curl -X POST http://localhost:5000/admin/api/schedule-group-messages \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 1,
    "message_type": "all"
  }'

# Schedule only morning messages
curl -X POST http://localhost:5000/admin/api/schedule-group-messages \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 1,
    "message_type": "morning",
    "message": "Good morning! Start your day with positivity! 🌅"
  }'
```

### Option 3: Using Admin CLI (Future Enhancement)

```bash
# This would be added to admin_cli.py
python admin_cli.py schedule-group 1 --type all
python admin_cli.py schedule-group 1 --type morning --date 2024-01-15
```

## Setting Up Your Motivational Group

1. **Create the Group:**
```bash
python manage_groups.py create_example
```

This creates a group with:
- Name: "Motivational Group"
- Scheduled times: Morning 8:00, Noon 12:00, Evening 18:00
- Custom welcome message

2. **Set as Default Group:**
Add to your `.env`:
```env
DEFAULT_GROUP_ID=1
```

3. **Schedule Messages:**
Use the `group_message_scheduler.py` functions or API to schedule messages.

## Database Fields

The system uses these fields to determine timezone matching:

- `message_delivery_preference`: 
  - `'on_demand'`: User requests messages
  - `'scheduled'`: Scheduled but NOT timezone-matched
  - `'scheduled_timezone'`: Scheduled WITH timezone matching
  
- `use_timezone_matching`: Boolean flag (True if user wants timezone matching)

- `timezone_offset_minutes`: User's timezone offset from UTC (e.g., -300 for EST)

- `timezone_label`: Human-readable timezone (e.g., "EST", "PST")

## Important Notes

1. **Timezone Matching Only Works If:**
   - User selected "Scheduled + Timezone Match" during subscription
   - User provided their timezone during subscription
   - Admin schedules messages using the group scheduler functions

2. **Scheduling Individual Messages:**
   - When scheduling via admin panel for a single subscriber, the system automatically checks their preference
   - If they chose timezone matching, the input time is treated as their local time
   - If they didn't, the input time is treated as UTC

3. **Group Messages:**
   - The `schedule_group_messages()` function automatically handles timezone matching
   - It checks each subscriber's preference and schedules accordingly
   - Returns counts of how many were timezone-matched vs not

## Testing

To test timezone matching:

1. Create test subscribers with different timezones
2. Some choose "Scheduled + Timezone Match", others choose "Scheduled"
3. Schedule group messages
4. Check the scheduled times in the database - they should be different UTC times for timezone-matched users

## Summary

✅ Users can choose whether they want timezone matching or not
✅ If they choose timezone matching, morning messages arrive at morning in their timezone
✅ If they don't choose timezone matching, all users get messages at the same UTC time
✅ The system automatically handles the conversion based on user preference

