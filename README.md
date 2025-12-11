# Subscription Service Bot

A subscription service bot that collects subscriber information, manages $1.60/month subscriptions via **Stripe, PayPal, and Cryptocurrency**, and sends scheduled SMS messages using email-to-SMS gateways.

## Features

- 🤖 **Telegram Bot Interface**: Interactive bot for easy subscriber onboarding
- 📱 **Email-to-SMS Integration**: Sends SMS messages via carrier email gateways (e.g., `1234567890@myboostmobile.com`)
- 💳 **Multiple Payment Methods**: 
  - **Stripe**: Credit/debit card subscriptions
  - **PayPal**: PayPal billing agreements
  - **Cryptocurrency**: Coinbase Commerce integration + manual wallet payments (BTC, ETH, USDC, USDT)
- 📅 **Scheduled Messaging**: Schedule messages to be sent at specific times
- 👥 **Subscriber Management**: Collect and manage subscriber information
- 🔄 **Webhook Support**: Handles webhooks for all payment providers
- 🛠️ **Admin CLI**: Command-line interface for subscriber and message management

## Admin CLI

Command-line interface ব্যবহার করে subscriber management, message sending, এবং statistics দেখতে পারবেন।

### Quick Start

```bash
# View all commands
python admin_cli.py --help

# View statistics
python admin_cli.py stats

# List all subscribers
python admin_cli.py list

# Send message to subscriber
python admin_cli.py send 1 --message "Hello!"

# Schedule a message
python admin_cli.py schedule 1 --message "Reminder" --time "2024-01-15T10:00:00"
```

বিস্তারিত documentation এর জন্য `ADMIN_CLI.md` দেখুন।

## Deployment

### Railway Deployment
Railway-তে deploy করার জন্য `RAILWAY_DEPLOY.md` দেখুন।

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the root directory:

```env
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_PRICE_ID=price_xxxxxxxxxxxxx  # Optional: Pre-created price ID

# PayPal Configuration
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_MODE=sandbox  # sandbox or live
PAYPAL_WEBHOOK_ID=your_webhook_id

# Coinbase Commerce (Cryptocurrency)
COINBASE_COMMERCE_API_KEY=your_coinbase_api_key
COINBASE_COMMERCE_WEBHOOK_SECRET=your_webhook_secret

# Cryptocurrency Wallet Addresses (for manual payments)
BTC_WALLET_ADDRESS=your_btc_wallet_address
ETH_WALLET_ADDRESS=your_eth_wallet_address
USDC_WALLET_ADDRESS=your_usdc_wallet_address
USDT_WALLET_ADDRESS=your_usdt_wallet_address

# SMTP Configuration (for sending emails/SMS)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com

# Database
DATABASE_URL=sqlite:///subscription_service.db

# Server
SECRET_KEY=your-secret-key-here
BASE_URL=http://localhost:5000  # Your server URL for webhooks

# Telegram Bot (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### 3. Stripe Setup

1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe dashboard
3. Create a product and price in Stripe for $1.60/month subscription
4. Set up webhook endpoint at `http://your-domain.com/api/stripe-webhook`
5. Add webhook events: `customer.subscription.updated`, `customer.subscription.deleted`

### 4. PayPal Setup

1. Create a PayPal Developer account at https://developer.paypal.com
2. Create an app to get Client ID and Secret
3. Set up webhook endpoint at `http://your-domain.com/api/paypal-webhook`
4. Subscribe to events: `BILLING.SUBSCRIPTION.ACTIVATED`, `BILLING.SUBSCRIPTION.CANCELLED`, `BILLING.SUBSCRIPTION.PAYMENT.FAILED`

### 5. Coinbase Commerce Setup (Optional)

1. Create a Coinbase Commerce account at https://commerce.coinbase.com
2. Get your API key from the dashboard
3. Set up webhook endpoint at `http://your-domain.com/api/crypto-webhook`
4. Configure webhook secret

### 6. Gmail App Password (if using Gmail)

1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account > Security > App Passwords
3. Generate an app password for "Mail"
4. Use this password in `SMTP_PASSWORD`

### 7. Telegram Bot Setup (Optional)

1. Create a Telegram bot by messaging [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command and follow the instructions
3. Copy the bot token and add it to your `.env` file
4. The bot will automatically start when you run the application

### 8. Run the Application

```bash
python app.py
```

The server will start on `http://localhost:5000` and the Telegram bot will start automatically if a token is configured.

## API Endpoints

### Get Available Carriers
```http
GET /api/carriers
```

Returns list of supported carriers and their email-to-SMS gateway formats.

### Create Subscriber (with Payment Method)

#### Stripe Payment
```http
POST /api/subscribe
Content-Type: application/json

{
  "phone_number": "1234567890",
  "carrier": "boost",
  "email": "user@example.com",
  "name": "John Doe",
  "payment_method": "stripe"
}
```

#### PayPal Payment
```http
POST /api/subscribe
Content-Type: application/json

{
  "phone_number": "1234567890",
  "carrier": "boost",
  "email": "user@example.com",
  "name": "John Doe",
  "payment_method": "paypal"
}
```

Returns an `approval_url` that the user needs to visit to approve the PayPal subscription.

#### Cryptocurrency Payment (Coinbase Commerce)
```http
POST /api/subscribe
Content-Type: application/json

{
  "phone_number": "1234567890",
  "carrier": "boost",
  "email": "user@example.com",
  "name": "John Doe",
  "payment_method": "crypto",
  "crypto_type": "coinbase"
}
```

#### Cryptocurrency Payment (Manual Wallet)
```http
POST /api/subscribe
Content-Type: application/json

{
  "phone_number": "1234567890",
  "carrier": "boost",
  "email": "user@example.com",
  "name": "John Doe",
  "payment_method": "crypto",
  "crypto_type": "manual",
  "currency": "BTC"
}
```

### PayPal Approval
```http
POST /api/paypal/approve
Content-Type: application/json

{
  "subscriber_id": 1,
  "payer_id": "paypal_payer_id_from_redirect"
}
```

Execute PayPal billing agreement after user approval.

### Get Crypto Wallets
```http
GET /api/crypto/wallets
```

Returns wallet addresses for manual cryptocurrency payments.

### Verify Crypto Payment
```http
POST /api/crypto/verify
Content-Type: application/json

{
  "subscriber_id": 1,
  "transaction_hash": "0x1234..."
}
```

Manually verify and activate crypto subscription after payment confirmation.

### Get All Subscribers
```http
GET /api/subscribers
```

Returns list of all subscribers.

### Get Subscriber
```http
GET /api/subscribers/{id}
```

Returns details for a specific subscriber.

### Send SMS
```http
POST /api/subscribers/{id}/send-sms
Content-Type: application/json

{
  "message": "Hello, this is a test message!"
}
```

Sends an immediate SMS to the subscriber.

### Schedule Message
```http
POST /api/subscribers/{id}/schedule-message
Content-Type: application/json

{
  "message": "This is a scheduled message",
  "scheduled_time": "2024-12-25T10:00:00Z"
}
```

Schedules a message to be sent at a specific time.

### Cancel Subscription
```http
DELETE /api/subscribers/{id}
```

Cancels subscription and deletes subscriber.

### Webhooks
- `POST /api/stripe-webhook` - Stripe webhook events
- `POST /api/paypal-webhook` - PayPal webhook events
- `POST /api/crypto-webhook` - Coinbase Commerce webhook events

## Supported Payment Methods

### 1. Stripe
- Automatic recurring billing
- Credit/debit card support
- Webhook-based subscription updates

### 2. PayPal
- PayPal billing agreements
- Recurring monthly payments
- User approval flow via approval URL

### 3. Cryptocurrency
Two options:
- **Coinbase Commerce**: Automated checkout with multiple crypto support
- **Manual Wallets**: Direct wallet payments (BTC, ETH, USDC, USDT) with manual verification

## Supported Carriers

The bot supports the following carriers for email-to-SMS:

- AT&T (`att`)
- Verizon (`verizon`)
- T-Mobile (`t-mobile`)
- Sprint (`sprint`)
- Boost Mobile (`boost`)
- Cricket (`cricket`)
- MetroPCS (`metropcs`)
- TracFone (`tracfone`)
- US Cellular (`uscellular`)
- Virgin Mobile (`virgin`)
- Xfinity Mobile (`xfinity`)
- Google Fi (`googlefi`)
- And more...

See `email_sms_gateways.py` for the complete list.

## Database Schema

### Subscribers
- `id`: Primary key
- `phone_number`: 10-digit phone number
- `carrier`: Carrier name
- `email`: Subscriber email
- `name`: Subscriber name
- `sms_email`: Generated email-to-SMS address
- `payment_method`: stripe, paypal, or crypto
- `stripe_customer_id`, `stripe_subscription_id`: Stripe IDs
- `paypal_subscription_id`, `paypal_billing_agreement_id`: PayPal IDs
- `crypto_payment_address`, `crypto_transaction_hash`: Crypto payment info
- `subscription_status`: active, inactive, canceled, past_due, pending
- `created_at`, `updated_at`: Timestamps

### ScheduledMessages
- `id`: Primary key
- `subscriber_id`: Foreign key to subscribers
- `message`: Message text
- `scheduled_time`: When to send
- `sent`: Boolean flag
- `sent_at`: Timestamp when sent

### Subscriptions
- `id`: Primary key
- `subscriber_id`: Foreign key to subscribers
- `payment_method`: stripe, paypal, or crypto
- Payment provider-specific fields (Stripe, PayPal, or Crypto)
- `status`: Subscription status
- `current_period_start`, `current_period_end`: Billing period

## Usage Examples

### Subscribe with Stripe
```python
import requests

response = requests.post('http://localhost:5000/api/subscribe', json={
    'phone_number': '1234567890',
    'carrier': 'boost',
    'email': 'user@example.com',
    'name': 'John Doe',
    'payment_method': 'stripe'
})
```

### Subscribe with PayPal
```python
response = requests.post('http://localhost:5000/api/subscribe', json={
    'phone_number': '1234567890',
    'carrier': 'boost',
    'email': 'user@example.com',
    'name': 'John Doe',
    'payment_method': 'paypal'
})

# Redirect user to response['subscription']['approval_url']
# After approval, execute with payer_id:
requests.post('http://localhost:5000/api/paypal/approve', json={
    'subscriber_id': response['subscriber']['id'],
    'payer_id': 'payer_id_from_paypal'
})
```

### Subscribe with Crypto (Coinbase)
```python
response = requests.post('http://localhost:5000/api/subscribe', json={
    'phone_number': '1234567890',
    'carrier': 'boost',
    'email': 'user@example.com',
    'name': 'John Doe',
    'payment_method': 'crypto',
    'crypto_type': 'coinbase'
})

# Redirect user to response['subscription']['checkout_url']
```

### Subscribe with Crypto (Manual)
```python
response = requests.post('http://localhost:5000/api/subscribe', json={
    'phone_number': '1234567890',
    'carrier': 'boost',
    'email': 'user@example.com',
    'name': 'John Doe',
    'payment_method': 'crypto',
    'crypto_type': 'manual',
    'currency': 'BTC'
})

# Get wallet address from response['subscription']['payment_info']['wallet_address']
# After payment, verify with transaction hash:
requests.post('http://localhost:5000/api/crypto/verify', json={
    'subscriber_id': response['subscriber']['id'],
    'transaction_hash': '0x1234...'
})
```

## Notes

- Phone numbers must be 10 digits (no country code, no formatting)
- Subscribers must have active subscriptions to receive messages
- Messages are checked and sent every minute by the scheduler
- Make sure your SMTP credentials are correct for email sending
- Webhooks require HTTPS in production (use ngrok for testing)
- PayPal requires user approval before subscription activation
- Manual crypto payments require manual verification

## License

MIT
