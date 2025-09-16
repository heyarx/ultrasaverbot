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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # add in Render ENV

# FastAPI app
app = FastAPI()

# Telegram Application
application = Application.builder().token(TOKEN).build()

# --- Languages (21) ---
languages = [
    "English","Hindi","Spanish","French","German","Italian","Portuguese","Russian",
    "Chinese","Japanese","Korean","Arabic","Turkish","Bengali","Urdu","Tamil","Telugu",
    "Malayalam","Indonesian","Thai","Vietnamese"
]

# Build language buttons
def language_keyboard():
    buttons = []
    for i in range(0, len(languages), 3):
        row = [
            InlineKeyboardButton(text=lang, callback_data=f"lang_{lang}")
            for lang in languages[i:i+3]
        ]
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user.first_name else "User"

    # Typing animation
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(1.5)

    await update.message.reply_text(
        f"👋 Hello {name}!\nWelcome to the Media Downloader Bot.\n\n"
        "Please select your preferred language:",
        reply_markup=language_keyboard()
    )

# --- Handle Language Selection ---
async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    await context.bot.send_chat_action(chat_id=query.message.chat.id, action="typing")
    await asyncio.sleep(1)
    await query.edit_message_text(f"✅ Language set to **{lang}**.\n\nNow send me a link from YouTube, Instagram, Twitter or Facebook!")

# --- Handle URL ---
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("⏳ Downloading... please wait...")

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            "outtmpl": f"{tmpdir}/%(title)s.%(ext)s",
            "format": "bestvideo+bestaudio/best",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

            with open(file_path, 'rb') as f:
                await update.message.reply_document(document=f)

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(select_language, pattern=r"^lang_"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

# FastAPI endpoint
@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    await application.update_queue.put(Update.de_json(data, application.bot))
    return {"ok": True}

# Startup event: auto-set webhook
@app.on_event("startup")
async def startup_event():
    # Start the application
    asyncio.create_task(application.start())
    # Auto set webhook
    await application.bot.set_webhook(url=WEBHOOK_URL)

@app.on_event("shutdown")
async def shutdown_event():
    await application.stop()
