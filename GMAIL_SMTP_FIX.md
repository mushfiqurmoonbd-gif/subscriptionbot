# Gmail SMTP Error Fix Guide (বাংলা)

## সমস্যা:
```
SMTP Authentication failed: (535, b'5.7.8 Username and Password not accepted')
```

## সমাধান:

### Step 1: Gmail Account এ 2-Factor Authentication Enable করুন

1. **Gmail Account এ Login করুন**: https://myaccount.google.com
2. **Security** section এ যান
3. **2-Step Verification** enable করুন
4. Phone number verify করুন

### Step 2: App Password Generate করুন

1. **Google Account Security Page** এ যান: https://myaccount.google.com/security
2. **2-Step Verification** section এ click করুন
3. Scroll down করে **App passwords** section খুঁজুন
4. **App passwords** এ click করুন
5. **Select app** dropdown থেকে **Mail** select করুন
6. **Select device** dropdown থেকে **Other (Custom name)** select করুন
7. Name দিন: `Subscription Service Bot`
8. **Generate** button click করুন
9. **16-character password** copy করুন (যেমন: `abcd efgh ijkl mnop`)

### Step 3: .env File Update করুন

`.env` file এ এই format এ লিখুন (কোনো space বা quote ছাড়া):

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=moonbd01717@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM_EMAIL=moonbd01717@gmail.com
```

**Important:**
- Password এ কোনো space থাকবে না
- Password এ কোনো quote (`"` বা `'`) থাকবে না
- Password সরাসরি copy-paste করুন (space remove করুন)

### Step 4: Server Restart করুন

1. Flask app stop করুন (Ctrl+C)
2. আবার start করুন:
   ```bash
   python app.py
   ```

### Step 5: Test করুন

Admin panel থেকে একটি test message send করুন।

## Common Issues:

### Issue 1: "App passwords" option দেখা যাচ্ছে না
**Solution:** 
- 2-Step Verification enable করা আছে কিনা check করুন
- কিছুক্ষণ wait করুন (Google account update হতে সময় লাগতে পারে)

### Issue 2: Password copy করার সময় space আসছে
**Solution:**
- Password manually type করুন
- অথবা copy করে notepad এ paste করুন, তারপর space remove করুন

### Issue 3: Still error আসছে
**Solution:**
1. `.env` file check করুন - কোনো extra character আছে কিনা
2. Password আবার generate করুন
3. Server restart করুন
4. Browser cache clear করুন

## Verification:

Test করার জন্য terminal এ এই command run করুন:
```bash
python -c "from config import Config; print('SMTP_USERNAME:', Config.SMTP_USERNAME); print('SMTP_PASSWORD:', Config.SMTP_PASSWORD[:4] + '****' if Config.SMTP_PASSWORD else 'NOT SET')"
```

## Alternative: Gmail এর পরিবর্তে অন্য SMTP ব্যবহার

যদি Gmail কাজ না করে, আপনি অন্য SMTP service ব্যবহার করতে পারেন:

### Outlook/Hotmail:
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your_email@outlook.com
SMTP_PASSWORD=your_password
SMTP_FROM_EMAIL=your_email@outlook.com
```

### SendGrid (Free tier available):
```env
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your_sendgrid_api_key
SMTP_FROM_EMAIL=your_verified_email@example.com
```

## Help:

যদি এখনও সমস্যা থাকে:
1. Terminal logs check করুন
2. `.env` file verify করুন
3. Gmail account security settings check করুন

