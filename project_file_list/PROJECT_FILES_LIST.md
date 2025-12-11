# Subscription Bot - Complete Project File List

## 📁 Project Structure

### 🔧 Core Application Files

#### Main Application
- **app.py** - Main Flask application entry point
- **config.py** - Configuration settings and environment variables
- **models.py** - Database models (Subscriber, ScheduledMessage, Subscription, etc.)

#### Telegram Bot
- **telegram_bot.py** - Telegram bot implementation with conversation handlers
- **bot.py** - Alternative bot implementation (async version)

#### Admin Panel
- **admin_routes.py** - Admin web panel routes and HTML interface
- **admin_cli.py** - Command-line admin interface

### 💳 Payment Integration

- **subscription_manager.py** - Stripe subscription management
- **paypal_manager.py** - PayPal payment integration
- **crypto_manager.py** - Cryptocurrency payment handling (Coinbase Commerce + manual)

### 📱 SMS/MMS Functionality

- **sms_sender.py** - SMS sending via email-to-SMS and Twilio (supports images/MMS)
- **email_sms_gateways.py** - Carrier email-to-SMS gateway mappings
- **scheduler.py** - Message scheduling system
- **group_message_scheduler.py** - Group message scheduling with timezone matching

### 📦 Subscription Management

- **plan_manager.py** - Subscription plan management
- **delivery_messages.py** - Message templates for delivery confirmations

### 🗄️ Database

- **models.py** - All database models
- **init_database.py** - Database initialization script
- **migrate_database.py** - Database migration script
- **clear_database.py** - Database clearing utility

### 🛠️ Utility Scripts

- **check_setup.py** - Setup verification script
- **fix_bot_conflict.py** - Bot conflict resolution
- **example_usage.py** - Example API usage code
- **manage_groups.py** - Service group management script

### 📨 SMS Testing Scripts

- **send_bd_sms.py** - Bangladesh SMS sending test
- **send_bd_sms_twilio.py** - Twilio SMS test for Bangladesh
- **quick_send_bd.py** - Quick SMS test script

### 📄 Configuration Files

- **requirements.txt** - Python dependencies
- **runtime.txt** - Python runtime version
- **Procfile** - Heroku/Railway deployment configuration
- **railway.json** - Railway deployment configuration

### 📚 Documentation Files

#### Main Documentation
- **README.md** - Main project documentation
- **HOW_IT_WORKS.md** - System architecture and workflow
- **USER_GUIDE.md** - End-user guide
- **ADMIN_CLI.md** - Admin CLI documentation

#### Deployment Guides
- **RAILWAY_DEPLOY.md** - Railway deployment instructions
- **RUN_INSTRUCTIONS.md** - Running instructions

#### Feature Documentation
- **NEW_FEATURES.md** - New features documentation
- **TIMEZONE_MATCHING_GUIDE.md** - Timezone matching feature guide
- **PRICING_SYSTEM_SUMMARY.md** - Pricing system overview
- **GMAIL_SMTP_FIX.md** - Gmail SMTP setup guide

### 📂 Directories

- **instance/** - SQLite database storage (local development)
- **__pycache__/** - Python bytecode cache
- **uploads/** - Uploaded images for MMS (created at runtime)

---

## 📋 File Categories Summary

### Python Files (26 files)
1. app.py
2. admin_cli.py
3. admin_routes.py
4. bot.py
5. check_setup.py
6. clear_database.py
7. config.py
8. crypto_manager.py
9. delivery_messages.py
10. email_sms_gateways.py
11. example_usage.py
12. fix_bot_conflict.py
13. group_message_scheduler.py
14. init_database.py
15. manage_groups.py
16. migrate_database.py
17. models.py
18. paypal_manager.py
19. plan_manager.py
20. quick_send_bd.py
21. scheduler.py
22. send_bd_sms.py
23. send_bd_sms_twilio.py
24. sms_sender.py
25. subscription_manager.py
26. telegram_bot.py

### Documentation Files (10 files)
1. ADMIN_CLI.md
2. GMAIL_SMTP_FIX.md
3. HOW_IT_WORKS.md
4. NEW_FEATURES.md
5. PRICING_SYSTEM_SUMMARY.md
6. RAILWAY_DEPLOY.md
7. README.md
8. RUN_INSTRUCTIONS.md
9. TIMEZONE_MATCHING_GUIDE.md
10. USER_GUIDE.md

### Configuration Files (4 files)
1. Procfile
2. railway.json
3. requirements.txt
4. runtime.txt

### Other Files
1. GMAIL_SMTP_FIX.zip

---

## 🎯 Key Features by File

### Core Features
- **Multi-group support** (ServiceGroup model, manage_groups.py)
- **Timezone matching** (group_message_scheduler.py, TIMEZONE_MATCHING_GUIDE.md)
- **Message delivery preferences** (models.py, telegram_bot.py)
- **Photo/Image sending** (sms_sender.py, admin_routes.py)

### Payment Methods
- Stripe (subscription_manager.py)
- PayPal (paypal_manager.py)
- Cryptocurrency (crypto_manager.py)

### SMS Methods
- Email-to-SMS (email_sms_gateways.py, sms_sender.py)
- Twilio API (sms_sender.py)
- MMS support (sms_sender.py)

### Admin Tools
- Web Panel (admin_routes.py)
- CLI Tool (admin_cli.py)
- Group Management (manage_groups.py)

---

## 📝 Important Notes

1. **Database**: Uses SQLite locally, PostgreSQL on Railway
2. **Environment Variables**: Configured in `.env` file (not in repo)
3. **Uploads**: Images stored in `uploads/` directory
4. **Instance**: Database stored in `instance/` directory

---

## 🚀 Quick Start Files

To get started, focus on these files:
1. **README.md** - Overview
2. **config.py** - Configuration
3. **app.py** - Main application
4. **models.py** - Database structure
5. **requirements.txt** - Dependencies

---

*Last Updated: 2024*
*Total Files: 40+ files*

