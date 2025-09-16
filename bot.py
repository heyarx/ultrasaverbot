import os
import asyncio
import tempfile
from fastapi import FastAPI, Request
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
)
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # should be https://ultrasaverbot.onrender.com/webhook

app = FastAPI()
application = Application.builder().token(TOKEN).build()

# --- Languages (21) ---
languages = [
    "English","Hindi","Spanish","French","German","Italian","Portuguese","Russian",
    "Chinese","Japanese","Korean","Arabic","Turkish","Bengali","Urdu","Tamil","Telugu",
    "Malayalam","Indonesian","Thai","Vietnamese"
]

def language_keyboard():
    buttons = []
    for i in range(0, len(languages), 3):
        row = [
            InlineKeyboardButton(text=lang, callback_data=f"lang_{lang}")
            for lang in languages[i:i+3]
        ]
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def format_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 MP3 (Audio)", callback_data="format_mp3"),
            InlineKeyboardButton("🎥 MP4 (Video)", callback_data="format_mp4")
        ]
    ])

# Store user preferences in memory (simple dict)
user_prefs = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user.first_name else "User"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(1.5)
    await update.message.reply_text(
        f"👋 Hello {name}!\nWelcome to the Media Downloader Bot.\n\n"
        "Please select your preferred language:",
        reply_markup=language_keyboard()
    )

# Handle language selection
async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    lang = query.data.replace("lang_", "")
    user_prefs[user_id] = {"language": lang}
    await context.bot.send_chat_action(chat_id=query.message.chat.id, action="typing")
    await asyncio.sleep(1)
    await query.edit_message_text(
        f"✅ Language set to **{lang}**.\n\nNow choose the format you want:",
        reply_markup=format_keyboard()
    )

# Handle format selection
async def select_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    fmt = "mp3" if query.data == "format_mp3" else "mp4"
    if user_id not in user_prefs:
        user_prefs[user_id] = {}
    user_prefs[user_id]["format"] = fmt
    await context.bot.send_chat_action(chat_id=query.message.chat.id, action="typing")
    await asyncio.sleep(1)
    await query.edit_message_text(
        f"✅ Format set to **{fmt.upper()}**.\n\nNow send me a link from YouTube, Instagram, Twitter or Facebook!"
    )

# Download media
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prefs = user_prefs.get(user_id, {})
    fmt = prefs.get("format", "mp4")  # default mp4

    url = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("⏳ Downloading... please wait...")

    with tempfile.TemporaryDirectory() as tmpdir:
        if fmt == "mp3":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{tmpdir}/%(title)s.%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
        else:
            ydl_opts = {
                "outtmpl": f"{tmpdir}/%(title)s.%(ext)s",
                "format": "bestvideo+bestaudio/best",
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                if fmt == "mp3":
                    base, ext = os.path.splitext(file_path)
                    file_path = base + ".mp3"

            with open(file_path, 'rb') as f:
                await update.message.reply_document(document=f)

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(select_language, pattern=r"^lang_"))
application.add_handler(CallbackQueryHandler(select_format, pattern=r"^format_"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

# FastAPI endpoint at /webhook
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    await application.update_queue.put(Update.de_json(data, application.bot))
    return {"ok": True}

# Startup event: auto-set webhook
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(application.start())
    await application.bot.set_webhook(url=WEBHOOK_URL)

@app.on_event("shutdown")
async def shutdown_event():
    await application.stop()
