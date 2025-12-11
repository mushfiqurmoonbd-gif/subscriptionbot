
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SENDER_EMAIL = os.getenv('SENDER_EMAIL')
    # Get DATABASE_URL and ensure it uses aiosqlite for async SQLite
    _db_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./subscriptions.db')
    # Convert sqlite:// to sqlite+aiosqlite:// for async support
    if _db_url.startswith('sqlite:///'):
        _db_url = _db_url.replace('sqlite:///', 'sqlite+aiosqlite:///', 1)
    elif _db_url.startswith('sqlite://'):
        _db_url = _db_url.replace('sqlite://', 'sqlite+aiosqlite://', 1)
    DATABASE_URL = _db_url
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')

cfg = Config()

# ======== db.py ========
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime
import datetime

engine = create_async_engine(cfg.DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class Subscriber(Base):
    __tablename__ = 'subscribers'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, index=True, nullable=True)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=False)
    carrier = Column(String, nullable=False)
    sms_email = Column(String, nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscribed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# helper
async def get_subscriber_by_phone(session, phone):
    return (await session.execute(
        Subscriber.__table__.select().where(Subscriber.phone == phone)
    )).first()

# ======== email_sender.py ========
import asyncio
from email.message import EmailMessage
import aiosmtplib

async def send_sms_via_email(to_address: str, message: str):
    msg = EmailMessage()
    msg['From'] = cfg.SENDER_EMAIL
    msg['To'] = to_address
    msg['Subject'] = ''
    msg.set_content(message)
    await aiosmtplib.send(msg, hostname=cfg.SMTP_HOST, port=cfg.SMTP_PORT,
                           username=cfg.SMTP_USER, password=cfg.SMTP_PASSWORD, start_tls=True)

# ======== payments.py ========
import stripe
stripe.api_key = cfg.STRIPE_API_KEY

PRICE_ID = 'price_monthly_1_60_usd_placeholder'  # Create this in Stripe dashboard

async def create_checkout_session(customer_email, phone, success_url=None, cancel_url=None):
    # Create a customer then a checkout session for subscription
    customer = stripe.Customer.create(email=customer_email, metadata={'phone': phone})
    session = stripe.checkout.Session.create(
        customer=customer.id,
        mode='subscription',
        line_items=[{'price': PRICE_ID, 'quantity': 1}],
        success_url=success_url or cfg.BASE_URL + '/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=cancel_url or cfg.BASE_URL + '/cancel',
    )
    return session

# Webhook handler (FastAPI route will call)
from fastapi import HTTPException

def handle_stripe_event(event):
    # Minimal handling: subscription created, invoice.payment_failed, customer.subscription.deleted
    typ = event['type']
    data = event['data']['object']
    return typ, data

# ======== scheduler.py ========
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

scheduler = AsyncIOScheduler()

async def start_scheduler(send_fn):
    # send_fn should be an async function accepting (to_address, message)
    # Example: schedule daily message to everyone
    async def job_all():
        async with AsyncSessionLocal() as session:
            result = await session.execute(Subscriber.__table__.select().where(Subscriber.subscribed == True))
            rows = result.fetchall()
            for r in rows:
                to = r._mapping['sms_email']
                # customize message per user if needed
                await send_fn(to, "Your scheduled message from Bot")

    scheduler.add_job(job_all, CronTrigger(hour=9, minute=0))  # daily at 09:00 server time
    scheduler.start()

# ======== telecom_gateways.py ========
# Minimal mapping. Replace with your full list.
CARRIER_GATEWAYS = {
    'boost': 'myboostmobile.com',
    'att': 'txt.att.net',
    'verizon': 'vtext.com',
    'tmobile': 'tmomail.net',
}

def build_sms_email(phone: str, carrier_key: str):
    domain = CARRIER_GATEWAYS.get(carrier_key.lower())
    if not domain:
        raise ValueError('Unknown carrier')
    cleaned = ''.join(ch for ch in phone if ch.isdigit())
    return f"{cleaned}@{domain}"

# ======== bot_main.py ========
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import asyncio

TELEGRAM_TOKEN = cfg.TELEGRAM_TOKEN

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send /subscribe to begin subscription.")

async def subscribe_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your full name:")
    return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Very small stateful example using user_data
    user_data = context.user_data
    text = update.message.text.strip()
    if 'awaiting_name' not in user_data:
        user_data['awaiting_name'] = True
        user_data['name'] = text
        await update.message.reply_text('Thanks. Now send your phone number (digits only or with +):')
        user_data['awaiting_phone'] = True
        return
    if user_data.get('awaiting_phone'):
        phone = ''.join(ch for ch in text if ch.isdigit())
        user_data['phone'] = phone
        # ask carrier selection
        buttons = [InlineKeyboardButton(k.title(), callback_data=f'carrier::{k}') for k in CARRIER_GATEWAYS.keys()]
        kb = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
        await update.message.reply_text('Choose your carrier:', reply_markup=kb)
        return

async def carrier_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith('carrier::'):
        carrier = data.split('::', 1)[1]
        context.user_data['carrier'] = carrier
        phone = context.user_data['phone']
        sms_email = build_sms_email(phone, carrier)
        context.user_data['sms_email'] = sms_email
        # Create Stripe checkout session (web link)
        # In real app collect user email; here we'll reuse telegram username as a fallback
        email = update.effective_user.username or f'tg_{update.effective_user.id}@example.com'
        session = await asyncio.to_thread(create_checkout_session, email, phone)
        checkout_url = session.url
        await query.edit_message_text(f"Ready to subscribe. Click to pay: {checkout_url}")
        # Save partial data to DB after payment webhook confirms

async def main_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('subscribe', subscribe_start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(CallbackQueryHandler(carrier_selected))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    # Keep running
    await asyncio.Event().wait()

# ======== server.py (FastAPI) ========
from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
import json

app = FastAPI()

@app.on_event('startup')
async def startup_event():
    await init_db()
    # start scheduler with email sender
    await start_scheduler(send_sms_via_email)

@app.post('/stripe/webhook')
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get('stripe-signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig, cfg.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    typ, data = handle_stripe_event(event)
    # Example: handle subscription created
    if typ == 'checkout.session.completed':
        session = data
        # Retrieve customer, metadata (phone)
        cust_id = session.get('customer')
        # You would now find the phone/metadata and mark user subscribed in DB
    return {'ok': True}

@app.get('/')
async def index():
    return {'status': 'ok'}

# ======== run.py ========
import asyncio

if __name__ == '__main__':
    # Run both FastAPI server and Telegram bot concurrently
    import multiprocessing
    async def runner():
        # start bot
        bot_task = asyncio.create_task(main_bot())
        # start uvicorn server in thread/subprocess
        from uvicorn import Config, Server
        config = Config('server:app', host='0.0.0.0', port=8000, log_level='info')
        server = Server(config)
        srv_task = asyncio.create_task(server.serve())
        await asyncio.gather(bot_task, srv_task)

    asyncio.run(runner())

# ======== README.md ========
# Telegram SMS Subscription Bot

# Quick start:
# 1. Create a Stripe product with a recurring price $1.60/month and set PRICE_ID in payments.py.
# 2. Fill .env with your keys and SMTP credentials.
# 3. Install dependencies: pip install -r requirements.txt
# 4. Run: python run.py

# Notes & next steps:
# - Add robust DB helpers for upsert, get by telegram id, handle webhook events to link payments to subscribers.
# - Add verification: send confirmation SMS email upon successful subscription.
# - Implement retry logic for failed payments, webhooks security, logging and admin panel.
# - Respect local laws: send consent and unsubscribe instructions in every message to comply with spam laws.

# End of skeleton
