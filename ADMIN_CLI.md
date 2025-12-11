# Admin CLI Guide

Admin CLI tool ব্যবহার করে subscriber management, message management, এবং statistics দেখতে পারবেন।

## Installation

CLI ব্যবহার করার জন্য dependencies install করুন:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Commands

#### 1. List All Subscribers
```bash
python admin_cli.py list
```

**Filter by status:**
```bash
python admin_cli.py list --status active
python admin_cli.py list --status pending
python admin_cli.py list --status cancelled
```

**Output:**
- Table format এ সব subscribers এর list
- Status summary
- Payment method summary

#### 2. Show Subscriber Details
```bash
python admin_cli.py show <subscriber_id>
```

**Example:**
```bash
python admin_cli.py show 1
```

**Shows:**
- Subscriber information
- Payment method details (Stripe/PayPal/Crypto)
- Subscription history
- Scheduled messages

#### 3. Send Message to Subscriber
```bash
python admin_cli.py send <subscriber_id> --message "Your message here"
```

**Options:**
- `--message` or `-m`: Message text (required)
- `--confirm` or `-y`: Skip confirmation prompt

**Example:**
```bash
python admin_cli.py send 1 --message "Hello! This is a test message."
python admin_cli.py send 1 --message "Hello!" --confirm
```

#### 4. Schedule a Message
```bash
python admin_cli.py schedule <subscriber_id> --message "Your message" --time "2024-01-15T10:00:00"
```

**Options:**
- `--message` or `-m`: Message text (required)
- `--time` or `-t`: Scheduled time in ISO format (YYYY-MM-DDTHH:MM:SS)
  - If not provided, defaults to 1 hour from now

**Example:**
```bash
# Schedule for specific time
python admin_cli.py schedule 1 --message "Reminder" --time "2024-01-15T14:30:00"

# Schedule for 1 hour from now (default)
python admin_cli.py schedule 1 --message "Reminder"
```

#### 5. Update Subscriber Status
```bash
python admin_cli.py update-status <subscriber_id> --status <status>
```

**Available statuses:**
- `active`
- `pending`
- `cancelled`
- `expired`
- `inactive`

**Example:**
```bash
python admin_cli.py update-status 1 --status active
python admin_cli.py update-status 1 --status cancelled
```

#### 6. Delete Subscriber
```bash
python admin_cli.py delete <subscriber_id>
```

**Options:**
- `--force` or `-f`: Skip confirmation prompt

**Example:**
```bash
python admin_cli.py delete 1
python admin_cli.py delete 1 --force
```

**Note:** This will also delete:
- All scheduled messages
- All subscription records

#### 7. List Scheduled Messages
```bash
python admin_cli.py messages
```

**Options:**
- `--sent`: Show only sent messages
- `--pending`: Show only pending messages
- `--subscriber-id <id>`: Filter by subscriber ID

**Examples:**
```bash
# All messages
python admin_cli.py messages

# Only pending messages
python admin_cli.py messages --pending

# Only sent messages
python admin_cli.py messages --sent

# Messages for specific subscriber
python admin_cli.py messages --subscriber-id 1
```

#### 8. View Statistics
```bash
python admin_cli.py stats
```

**Shows:**
- Total subscribers
- Active/Pending/Cancelled counts
- Payment method breakdown (Stripe/PayPal/Crypto)
- Message statistics (total, sent, pending)
- Subscription statistics
- Recent activity

#### 9. Export Subscribers to CSV
```bash
python admin_cli.py export
python admin_cli.py export --output subscribers.csv
```

**Options:**
- `--output` or `-o`: Output filename (default: `subscribers_YYYYMMDD_HHMMSS.csv`)

**Example:**
```bash
python admin_cli.py export --output my_subscribers.csv
```

**Exported fields:**
- id, name, phone_number, carrier, email
- status, payment_method
- created_at, telegram_user_id, telegram_username

## Examples

### Complete Workflow Example

```bash
# 1. Check statistics
python admin_cli.py stats

# 2. List all active subscribers
python admin_cli.py list --status active

# 3. View subscriber details
python admin_cli.py show 1

# 4. Send immediate message
python admin_cli.py send 1 --message "Hello! Welcome to our service."

# 5. Schedule a reminder
python admin_cli.py schedule 1 --message "Don't forget to check your messages!" --time "2024-01-20T09:00:00"

# 6. Check scheduled messages
python admin_cli.py messages --subscriber-id 1

# 7. Update status if needed
python admin_cli.py update-status 1 --status active

# 8. Export all subscribers
python admin_cli.py export --output all_subscribers.csv
```

### Quick Reference

```bash
# View all commands
python admin_cli.py --help

# View help for specific command
python admin_cli.py list --help
python admin_cli.py send --help
```

## Tips

1. **Always check stats first** to get overview:
   ```bash
   python admin_cli.py stats
   ```

2. **Use filters** to narrow down results:
   ```bash
   python admin_cli.py list --status active
   python admin_cli.py messages --pending
   ```

3. **Use --confirm flag** for automation:
   ```bash
   python admin_cli.py send 1 --message "Test" --confirm
   ```

4. **Export regularly** for backups:
   ```bash
   python admin_cli.py export --output backup_$(date +%Y%m%d).csv
   ```

5. **Check subscriber details** before sending messages:
   ```bash
   python admin_cli.py show 1
   ```

## Troubleshooting

### Database Connection Error
- Ensure `.env` file is configured correctly
- Check `DATABASE_URL` is set (for PostgreSQL)
- For SQLite, ensure database file exists

### Module Not Found Error
- Install dependencies: `pip install -r requirements.txt`
- Ensure `tabulate` is installed: `pip install tabulate`

### Permission Error
- Ensure you have write permissions for CSV exports
- Check database permissions

### Subscriber Not Found
- List all subscribers first: `python admin_cli.py list`
- Check subscriber ID is correct

## Notes

- All timestamps are in UTC
- Messages are sent immediately when using `send` command
- Scheduled messages are processed by the scheduler (running in app)
- Status updates are saved immediately
- Deleted subscribers cannot be recovered

