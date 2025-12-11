# কিভাবে রান করবেন (How to Run)

## ধাপ ১: Dependencies Install করুন

```bash
pip install -r requirements.txt
```

## ধাপ ২: Environment Variables Setup করুন

`.env` file তৈরি করুন project root এ:

```env
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_PRICE_ID=price_xxxxxxxxxxxxx

# PayPal Configuration
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_MODE=sandbox

# Coinbase Commerce (Cryptocurrency)
COINBASE_COMMERCE_API_KEY=your_coinbase_api_key
COINBASE_COMMERCE_WEBHOOK_SECRET=your_webhook_secret

# Cryptocurrency Wallet Addresses
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
SECRET_KEY=Rsj5sr0_rZ4uH9OQLFnxrQnC_zaWMHOJXcmmmPhiJMk
BASE_URL=http://localhost:5000

# Telegram Bot (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

## ধাপ ৩: Application Run করুন

### Option 1: Flask API Server (Main Application)

```bash
python app.py
```

এটি start করবে:
- Flask API server on `http://localhost:5000`
- Telegram bot (যদি TELEGRAM_BOT_TOKEN set করা থাকে)
- Message scheduler

### Option 2: শুধু Telegram Bot (যদি bot.py আলাদা থাকে)

```bash
python bot.py
```

## API Endpoints

একবার run করার পর, আপনি এই endpoints ব্যবহার করতে পারবেন:

- `http://localhost:5000/api/health` - Health check
- `http://localhost:5000/api/carriers` - Available carriers
- `http://localhost:5000/api/subscribe` - Subscribe endpoint (POST)
- `http://localhost:5000/api/subscribers` - Get all subscribers (GET)

## Telegram Bot Commands

যদি Telegram bot active থাকে:
- `/start` - Subscription process শুরু করুন
- `/status` - আপনার subscription status দেখুন
- `/help` - Help message

## Troubleshooting

### Error: Module not found
```bash
pip install -r requirements.txt
```

### Error: Database not found
Database automatically create হবে প্রথম run এ।

### Error: Telegram bot not starting
Check করুন `TELEGRAM_BOT_TOKEN` `.env` file এ set করা আছে কিনা।

### Port already in use
যদি port 5000 already use হয়, `app.py` file এ change করুন:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port
```

