import os
import json
import asyncio
from pathlib import Path
import logging
import yt_dlp
import requests

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

# ========== Logging ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Environment Variables ==========
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://ultrasaverbot.onrender.com")
COOKIES_PATH = os.environ.get("YT_COOKIES_FILE", "./cookies.txt")

# ========== FastAPI App ==========
app = FastAPI()

@app.get("/")
async def home():
    return PlainTextResponse("UltrasaverBot is running")

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """Main webhook endpoint that Telegram POSTs updates to."""
    update_data = await request.json()
    update = Update.de_json(update_data, application.bot)
    await application.update_queue.put(update)
    return PlainTextResponse("OK")

# ========== Handlers ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🇮🇳 English", callback_data="lang_en"),
         InlineKeyboardButton("🇮🇳 বাংলা", callback_data="lang_bn"),
         InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌟 Welcome! Please choose your language:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data
    user = update.effective_user
    if lang == "lang_en":
        msg = f"Hello {user.first_name}! 🎶 I can download videos or songs from YouTube, Facebook, Instagram… just send me the link or name."
    elif lang == "lang_bn":
        msg = f"হ্যালো {user.first_name}! 🎶 আমি ইউটিউব, ফেসবুক, ইনস্টাগ্রাম থেকে ভিডিও/গান ডাউনলোড করতে পারি… শুধু লিংক বা নাম দিন।"
    else:
        msg = f"नमस्ते {user.first_name}! 🎶 मैं यूट्यूब, फेसबुक, इंस्टाग्राम से वीडियो/गाने डाउनलोड कर सकता हूँ… बस लिंक या नाम भेजें।"
    await query.edit_message_text(msg)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 UltrasaverBot – Download music/videos from YouTube, Facebook, Instagram and more."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 Send me a song name or a link from YouTube, Facebook, Instagram etc. "
        "and I’ll download it for you."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Detect URL or search query
    if text.startswith("http://") or text.startswith("https://"):
        await download_video(update, text)
    else:
        await download_audio_from_search(update, text)

async def download_video(update: Update, url: str):
    await update.message.reply_text("⏳ Downloading video… please wait")
    ydl_opts = {
        "outtmpl": "%(title)s.%(ext)s",
        "cookies": COOKIES_PATH if Path(COOKIES_PATH).exists() else None,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        await update.message.reply_document(document=open(filename, "rb"))
    except Exception as e:
        logger.error(f"Video download error: {e}")
        await update.message.reply_text("⚠️ Error downloading the video.")

async def download_audio_from_search(update: Update, query: str):
    await update.message.reply_text(f"🔎 Searching and downloading audio for: {query}")
    search_url = f"ytsearch1:{query}"
    ydl_opts = {
        "outtmpl": "%(title)s.%(ext)s",
        "cookies": COOKIES_PATH if Path(COOKIES_PATH).exists() else None,
        "format": "bestaudio/best",
        "quiet": True,
        "postprocessors": [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=True)
            filename = ydl.prepare_filename(info['entries'][0])
        await update.message.reply_document(document=open(filename, "rb"))
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        await update.message.reply_text("⚠️ Error downloading the audio.")

# ========== Telegram Application ==========
application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("about", about))
application.add_handler(CommandHandler("help", help_cmd))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ========== Webhook Setup ==========
async def set_webhook():
    webhook_url = f"{WEBHOOK_URL}/telegram-webhook"
    logger.info(f"Setting webhook to: {webhook_url}")
    async with application.bot:
        await application.bot.set_webhook(url=webhook_url)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(set_webhook())
