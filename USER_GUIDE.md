# 📱 User Guide - SMS Subscription Service

## What You Get After Subscription

### ✅ After Payment Approval:

1. **Welcome Message** (via Telegram)
   - Confirmation that your subscription is active
   - Details about your subscription

2. **SMS Messages** (via Phone)
   - You'll receive SMS messages scheduled by admin
   - Messages are sent to your phone number: `{your_phone_number}`
   - Carrier: `{your_carrier}`

### 📨 How Messages Work:

- **Admin schedules messages** for all active subscribers
- Messages are sent to your phone via SMS
- You'll receive messages at scheduled times
- Only active subscribers receive messages

### 💰 Subscription Details:

- **Price**: $1.60/month
- **Payment Methods**: Stripe, PayPal, Crypto (BTC, ETH, USDC, USDT)
- **Status**: Check anytime with `/status` command in Telegram

### 🔔 What Happens:

1. **Subscribe**: Complete subscription process via Telegram bot
2. **Payment**: Pay using your preferred method
3. **Approval**: Admin approves your payment (for manual crypto payments)
4. **Activation**: Your subscription becomes active
5. **Receive Messages**: You start receiving scheduled SMS messages

### 📞 Support:

- Use `/help` in Telegram bot for commands
- Use `/status` to check your subscription status
- Contact admin for any issues

### ⚠️ Important Notes:

- **Only active subscribers** receive messages
- Messages are scheduled by admin (not automatic)
- Make sure your phone number and carrier are correct
- Keep your subscription active to continue receiving messages

---

## Telegram Bot Commands:

- `/start` - Start subscription process
- `/status` - Check your subscription status
- `/verify_payment` - Verify crypto payment (with transaction hash)
- `/help` - Show help message
- `/cancel` - Cancel current operation

---

## Example Flow:

1. User sends `/start` in Telegram
2. Provides phone number, carrier, email (optional), name (optional)
3. Selects payment method (Stripe/PayPal/Crypto)
4. Completes payment
5. Admin approves payment (for manual crypto)
6. User receives welcome message via Telegram
7. User starts receiving SMS messages scheduled by admin

---

**Note**: This is a manual SMS service where admin schedules and sends messages to all active subscribers. There are no automatic recurring messages - all messages are scheduled by admin.

