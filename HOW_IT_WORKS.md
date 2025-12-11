# কিভাবে কাজ করবে (How It Works)

## 📋 Overview

এই subscription service bot তিনটি উপায়ে কাজ করে:
1. **Telegram Bot** - Telegram এ interactive bot
2. **Web API** - HTTP requests দিয়ে subscribe করতে পারবেন
3. **Scheduled Messages** - Automatic SMS পাঠানো

---

## 🤖 Telegram Bot দিয়ে Subscribe (সবচেয়ে সহজ)

### Step 1: Telegram Bot খুঁজুন
1. Telegram এ আপনার bot token দিয়ে bot খুলুন
2. `/start` command দিন

### Step 2: Information দিন
Bot আপনাকে step-by-step জিজ্ঞেস করবে:
1. **Phone Number** - 10 digit (যেমন: 1234567890)
2. **Carrier** - আপনার phone service provider (Boost, AT&T, Verizon, etc.)
3. **Email** - Optional (স্কিপ করতে পারেন)
4. **Name** - Optional (স্কিপ করতে পারেন)
5. **Payment Method** - Stripe, PayPal, বা Crypto

### Step 3: Payment করুন
Bot payment link দেবে, সেখানে গিয়ে payment করুন।

### Step 4: Done! ✅
Subscription active হয়ে যাবে এবং আপনি SMS পেতে শুরু করবেন।

---

## 🌐 Web API দিয়ে Subscribe

### API Call Example:

```bash
# POST request to subscribe
curl -X POST http://localhost:5000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "1234567890",
    "carrier": "boost",
    "email": "user@example.com",
    "name": "John Doe",
    "payment_method": "stripe"
  }'
```

### Response:
```json
{
  "message": "Subscriber created successfully",
  "subscriber": {
    "id": 1,
    "phone_number": "1234567890",
    "carrier": "boost",
    "subscription_status": "active"
  },
  "subscription": {
    "id": "sub_xxx",
    "status": "active",
    "payment_method": "stripe"
  }
}
```

---

## 💰 Payment Methods

### 1. Stripe (Credit/Debit Card)
- User card information দেবে
- Monthly $1.60 automatic charge হবে
- Recurring subscription

### 2. PayPal
- PayPal account দিয়ে approve করতে হবে
- Monthly recurring payment
- PayPal approval link দেবে

### 3. Cryptocurrency
**Option A: Coinbase Commerce**
- Coinbase checkout page
- Multiple crypto currencies support

**Option B: Manual Wallet**
- Wallet address পাবেন
- Crypto send করার পর manually verify করতে হবে

---

## 📱 SMS কিভাবে পাঠানো হয়

### Email-to-SMS Gateway System

প্রত্যেক carrier এর একটা email gateway আছে:
- **Boost Mobile**: `1234567890@myboostmobile.com`
- **AT&T**: `1234567890@txt.att.net`
- **Verizon**: `1234567890@vtext.com`

### Process:
1. Bot phone number + carrier collect করে
2. SMS email address generate করে (যেমন: `1234567890@myboostmobile.com`)
3. Email send করে সেই address এ
4. Carrier email টাকে SMS এ convert করে
5. User এর phone এ SMS চলে যায়

---

## 📅 Scheduled Messages

### API দিয়ে Message Schedule করুন:

```bash
POST http://localhost:5000/api/subscribers/1/schedule-message
{
  "message": "This is a reminder!",
  "scheduled_time": "2024-12-25T10:00:00Z"
}
```

### Automatic Sending:
- Scheduler প্রতি minute এ check করে
- Scheduled time হলে SMS পাঠায়
- শুধু active subscribers কে পাঠায়

---

## 🔄 Workflow Diagram

```
User → Telegram Bot / API
  ↓
Collect Info (Phone, Carrier, Email, Name)
  ↓
Select Payment Method
  ↓
Payment Processing (Stripe/PayPal/Crypto)
  ↓
Subscription Active ✅
  ↓
SMS Service Ready 📱
  ↓
Scheduled Messages Send Automatically
```

---

## 📊 Database Structure

### Subscribers Table:
- `phone_number` - 10 digit phone
- `carrier` - Service provider
- `sms_email` - Generated email-to-SMS address
- `payment_method` - stripe/paypal/crypto
- `subscription_status` - active/inactive/pending/canceled

### Scheduled Messages Table:
- `subscriber_id` - Link to subscriber
- `message` - Message text
- `scheduled_time` - When to send
- `sent` - True/False

---

## 🎯 Example Use Cases

### Case 1: Telegram Bot
```
User: /start
Bot: Please enter your 10-digit phone number
User: 1234567890
Bot: Select your carrier [Buttons]
User: [Clicks Boost]
Bot: Enter email (or /skip)
User: user@example.com
Bot: Enter name (or /skip)
User: John Doe
Bot: Select payment method [Buttons]
User: [Clicks Stripe]
Bot: ✅ Subscription created! Payment link: ...
```

### Case 2: API Subscription
```python
import requests

response = requests.post('http://localhost:5000/api/subscribe', json={
    'phone_number': '1234567890',
    'carrier': 'boost',
    'payment_method': 'stripe'
})

print(response.json())
```

### Case 3: Send Scheduled Message
```python
# Schedule a message for tomorrow
from datetime import datetime, timedelta

scheduled_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"

requests.post('http://localhost:5000/api/subscribers/1/schedule-message', json={
    'message': 'Your reminder message!',
    'scheduled_time': scheduled_time
})
```

---

## 🛠️ Setup Steps

1. **Environment Variables** (.env file):
   ```env
   SECRET_KEY=your_secret_key
   TELEGRAM_BOT_TOKEN=your_bot_token
   STRIPE_SECRET_KEY=your_stripe_key
   SMTP_USERNAME=your_email
   SMTP_PASSWORD=your_password
   ```

2. **Run Application**:
   ```bash
   python app.py
   ```

3. **Test**:
   - Visit: `http://localhost:5000/`
   - Or use Telegram bot: `/start`

---

## 📝 Important Notes

1. **Phone Number Format**: অবশ্যই 10 digits, কোন formatting নেই
   - ✅ Correct: `1234567890`
   - ❌ Wrong: `(123) 456-7890` or `123-456-7890`

2. **Carrier Selection**: Supported carriers এর list আছে:
   - Boost, AT&T, Verizon, T-Mobile, Sprint, Cricket, etc.

3. **Payment**: Subscription active না হলে SMS পাঠাবে না

4. **SMS Sending**: Email-to-SMS gateway ব্যবহার করে, তাই SMTP credentials প্রয়োজন

---

## 🚀 Quick Start Guide

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure .env file**:
   - SECRET_KEY
   - TELEGRAM_BOT_TOKEN (optional)
   - Payment provider keys (Stripe/PayPal/Crypto)

3. **Run**:
   ```bash
   python app.py
   ```

4. **Test**:
   - Browser: `http://localhost:5000/api/health`
   - Telegram: `/start` command

---

## 💡 Tips

- Telegram bot সবচেয়ে user-friendly
- API বেশি flexible, automation এর জন্য ভালো
- Scheduled messages automatic, manual intervention লাগে না
- সব payment methods support করে, user choose করতে পারে

---

## ❓ FAQ

**Q: SMS কখন পাঠাবে?**
A: Scheduled time হলে automatically পাঠাবে, বা manually send করতে পারবেন।

**Q: Payment fail হলে কি হবে?**
A: Subscription status `past_due` হবে, payment fix করার পর active হবে।

**Q: Multiple subscribers add করতে পারব?**
A: হ্যাঁ, API দিয়ে bulk add করতে পারবেন।

**Q: SMS limit আছে?**
A: Carrier এর email gateway limit অনুযায়ী, সাধারণত per day limit থাকে।

