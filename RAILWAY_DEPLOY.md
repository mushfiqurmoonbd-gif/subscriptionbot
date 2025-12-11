# Railway Deployment Guide

এই guide অনুসরণ করে আপনার subscription service bot Railway-তে deploy করুন।

## প্রস্তুতি

### 1. Railway Account তৈরি করুন
- [Railway.app](https://railway.app) এ যান
- GitHub account দিয়ে sign up করুন

### 2. Database Setup
Railway-তে PostgreSQL database যোগ করুন:
- Railway dashboard থেকে "New" → "Database" → "PostgreSQL" নির্বাচন করুন
- Database automatically provision হবে

## Deployment Steps

### Step 1: GitHub Repository
1. আপনার code GitHub-এ push করুন:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

### Step 2: Railway Project তৈরি করুন
1. Railway dashboard এ যান
2. "New Project" click করুন
3. "Deploy from GitHub repo" নির্বাচন করুন
4. আপনার repository select করুন

### Step 3: Environment Variables Setup
Railway dashboard → Variables tab এ নিচের variables add করুন:

#### Required Variables:
```env
# Database (Railway automatically provides DATABASE_URL, but check if needed)
DATABASE_URL=postgresql://user:password@host:port/dbname

# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
BASE_URL=https://your-app-name.railway.app

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_... (optional)

# PayPal
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_MODE=live  # or sandbox
PAYPAL_WEBHOOK_ID=your_webhook_id

# Coinbase Commerce
COINBASE_COMMERCE_API_KEY=your_coinbase_api_key
COINBASE_COMMERCE_WEBHOOK_SECRET=your_webhook_secret

# Cryptocurrency Wallets (Optional)
BTC_WALLET_ADDRESS=your_btc_address
ETH_WALLET_ADDRESS=your_eth_address
USDC_WALLET_ADDRESS=your_usdc_address
USDT_WALLET_ADDRESS=your_usdt_address

# Email/SMS (for email-to-SMS gateways)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Twilio (for international SMS)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

#### Important Notes:
- **SECRET_KEY**: একটি strong random string generate করুন:
  ```python
  import secrets
  print(secrets.token_hex(32))
  ```
- **BASE_URL**: Railway আপনাকে automatically একটি URL দেবে, সেটা use করুন
- **DATABASE_URL**: Railway PostgreSQL add করলে automatically set হবে

### Step 4: Webhook URLs Setup
Deploy হওয়ার পর webhook URLs update করুন:

#### Stripe Webhook:
1. [Stripe Dashboard](https://dashboard.stripe.com/webhooks) → Add endpoint
2. URL: `https://your-app-name.railway.app/api/stripe-webhook`
3. Events: Select all events বা relevant ones
4. Signing secret copy করুন এবং `STRIPE_WEBHOOK_SECRET` এ add করুন

#### PayPal Webhook:
1. [PayPal Developer Dashboard](https://developer.paypal.com/dashboard)
2. Webhooks → Add webhook
3. URL: `https://your-app-name.railway.app/api/paypal-webhook`
4. Webhook ID copy করুন এবং `PAYPAL_WEBHOOK_ID` এ add করুন

#### Coinbase Commerce Webhook:
1. [Coinbase Commerce Dashboard](https://commerce.coinbase.com/)
2. Settings → Webhooks → Add webhook
3. URL: `https://your-app-name.railway.app/api/crypto-webhook`
4. Webhook secret copy করুন এবং `COINBASE_COMMERCE_WEBHOOK_SECRET` এ add করুন

### Step 5: Deploy
1. Railway automatically detect করবে `Procfile` এবং deploy শুরু করবে
2. Deploy logs দেখুন Railway dashboard → Deployments tab এ
3. Deploy complete হলে "View Logs" দেখুন

### Step 6: Domain Setup (Optional)
1. Railway dashboard → Settings → Domains
2. Custom domain add করুন (optional)

## Verification

Deploy হওয়ার পর test করুন:

1. **Health Check**: 
   ```
   https://your-app-name.railway.app/api/health
   ```

2. **API Info**:
   ```
   https://your-app-name.railway.app/
   ```

3. **Telegram Bot**: 
   - Telegram এ আপনার bot-এ message পাঠান
   - `/start` command test করুন

## Troubleshooting

### Database Connection Error:
- Railway dashboard → Database → Connect → Connection URL copy করুন
- `DATABASE_URL` variable এ paste করুন

### Port Error:
- Railway automatically `PORT` environment variable provide করে
- Code already updated হয়েছে to use `PORT` variable

### Telegram Bot Not Working:
- Ensure `TELEGRAM_BOT_TOKEN` correctly set
- Check Railway logs for errors
- Bot may need few minutes to start

### Webhooks Not Working:
- Ensure `BASE_URL` is correct
- Check webhook URLs in payment provider dashboards
- Verify webhook secrets match

### SMS Not Sending:
- Check SMTP credentials (for email-to-SMS)
- Check Twilio credentials (for international SMS)
- Verify phone number format (+country_code)

## Monitoring

Railway dashboard থেকে:
- **Metrics**: CPU, Memory usage দেখুন
- **Logs**: Real-time logs দেখুন
- **Deployments**: Deploy history দেখুন

## Updates

Code update করতে:
1. GitHub এ push করুন
2. Railway automatically redeploy করবে
3. Deploy logs দেখুন

## Cost

Railway pricing:
- Free tier: $5 credit/month
- Hobby plan: $5/month
- Pro plan: $20/month

Check [Railway Pricing](https://railway.app/pricing) for details.

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

