# New Features Summary

## Overview
This update adds several important features to manage multiple groups, customize messages, and give users control over message delivery preferences.

## 🎯 New Features

### 1. Message Delivery Preferences
Users can now choose how they want to receive messages:
- **On-Demand**: Request messages when they want (via command or button)
- **Scheduled**: Admin sends at scheduled times (not timezone-matched)
- **Scheduled + Timezone Match**: Messages matched to user's timezone (e.g., morning at 8 AM their local time)

**How it works:**
- During subscription, users select their delivery preference after timezone selection
- The preference is stored in the database
- For timezone-matched messages, the system uses the user's timezone to send messages at the right local time

### 2. Support Contact System
Users can now contact you for support:
- New `/support` command in Telegram bot
- Shows your Telegram username and/or email
- Can be configured per group or globally
- Replaces generic "contact support" messages

**Configuration:**
- Set `SUPPORT_TELEGRAM_USERNAME` in `.env` (e.g., "admin" or "@admin")
- Set `SUPPORT_EMAIL` in `.env`
- Or configure per group using `manage_groups.py`

### 3. Editable Start Messages
Start/welcome messages are now customizable per group:
- Each group can have its own welcome message
- Default message can be set in config
- Perfect for managing different groups (motivational, fitness, etc.)

**How to customize:**
- Use `manage_groups.py` to create/update groups
- Set `DEFAULT_START_MESSAGE` in `.env` for global default
- Each group can override with its own message

### 4. Multiple Groups Support
You can now manage multiple groups/services on the same website:
- Create different groups (e.g., "Motivational Group", "Fitness Group")
- Each group has its own:
  - Start message
  - Support contact info
  - Scheduled message times
  - Default plan
- Subscribers are associated with a group
- Set `DEFAULT_GROUP_ID` in `.env` to specify which group new subscribers join

**Example Use Cases:**
- Motivational Group: Morning/noon/evening messages
- Fitness Group: Workout reminders
- Business Group: Daily tips

## 📋 Database Changes

### New Columns in `subscribers` table:
- `message_delivery_preference`: 'on_demand', 'scheduled', or 'scheduled_timezone'
- `use_timezone_matching`: Boolean for timezone matching
- `group_id`: Foreign key to service_groups table

### New Table: `service_groups`
- `id`: Primary key
- `name`: Group name (e.g., "Motivational Group")
- `description`: Group description
- `start_message`: Custom welcome message
- `support_telegram_username`: Support Telegram contact
- `support_email`: Support email contact
- `is_active`: Whether group is active
- `default_plan_id`: Default subscription plan
- `scheduled_times`: JSON with scheduled times (e.g., {"morning": "08:00", "noon": "12:00", "evening": "18:00"})

## 🚀 Setup Instructions

### 1. Run Database Migration
```bash
python migrate_database.py
```

This will:
- Add new columns to subscribers table
- Create service_groups table
- Set default values for existing subscribers

### 2. Configure Support Contact (Optional)
Add to your `.env` file:
```env
SUPPORT_TELEGRAM_USERNAME=your_telegram_username
SUPPORT_EMAIL=support@yourdomain.com
DEFAULT_START_MESSAGE=Your custom welcome message here
DEFAULT_GROUP_ID=1  # Optional: Set default group ID
```

### 3. Create Your First Group
```bash
# Create an example motivational group
python manage_groups.py create_example

# Or create a custom group
python manage_groups.py create "Fitness Group" "Daily fitness tips" "Welcome to Fitness Group!..."
```

### 4. List Groups
```bash
python manage_groups.py list
```

## 📱 User Experience

### Subscription Flow (Updated)
1. User sends `/start`
2. Sees group-specific welcome message
3. Provides phone number
4. Selects carrier
5. (Optional) Provides email
6. (Optional) Provides name
7. Selects timezone
8. **NEW:** Selects delivery preference (On-Demand, Scheduled, or Scheduled + Timezone)
9. Selects subscription plan
10. (Optional) Enters discount code
11. Selects payment method
12. Completes payment

### New Commands
- `/support` - Shows support contact information

## 🎨 Example: Motivational Group Setup

For a motivational group that sends messages at morning (8 AM), noon (12 PM), and evening (6 PM) matched to user's timezone:

1. **Create the group:**
```bash
python manage_groups.py create_example
```

2. **Set as default group** (in `.env`):
```env
DEFAULT_GROUP_ID=1
```

3. **Users will:**
   - See motivational group welcome message
   - Select "Scheduled + Timezone Match" during subscription
   - Receive messages at 8 AM, 12 PM, and 6 PM in their local timezone

## 🔧 Admin Functions

### Managing Groups
- Create groups: `python manage_groups.py create <name> <description> <start_message>`
- List groups: `python manage_groups.py list`
- Update groups: Edit `manage_groups.py` and use `update_group()` function

### Viewing User Preferences
- Check `message_delivery_preference` column in subscribers table
- Check `use_timezone_matching` for timezone matching preference
- Check `group_id` to see which group a subscriber belongs to

## ⚠️ Important Notes

1. **Existing Subscribers**: After migration, existing subscribers will have:
   - `message_delivery_preference` = 'scheduled' (default)
   - `use_timezone_matching` = False
   - `group_id` = NULL (unless you set a default)

2. **Timezone Matching**: For timezone-matched messages, ensure you schedule messages considering the user's timezone offset stored in `timezone_offset_minutes`.

3. **Multiple Groups**: If you want to manage multiple groups, you'll need to:
   - Create groups using `manage_groups.py`
   - Set `DEFAULT_GROUP_ID` or manually assign subscribers to groups
   - Consider adding group selection to the subscription flow (future enhancement)

4. **On-Demand Messages**: The on-demand feature requires additional implementation for users to request messages. This is a foundation that can be extended.

## 🔮 Future Enhancements

- Group selection during subscription
- On-demand message request command (`/request_message`)
- Admin panel UI for managing groups
- Bulk message scheduling with timezone matching
- Group-specific message templates

