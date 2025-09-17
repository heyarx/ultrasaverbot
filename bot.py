import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ✅ your Telegram Bot Token
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://ultrasaverbot.onrender.com/webhook")

app = FastAPI()

# Create Telegram Application
application = Application.builder().token(BOT_TOKEN).build()

# Supported languages (21)
LANGUAGES = [
    "English", "Hindi", "Spanish", "French", "German",
    "Italian", "Portuguese", "Russian", "Chinese", "Japanese",
    "Korean", "Arabic", "Turkish", "Indonesian", "Vietnamese",
    "Thai", "Bengali", "Urdu", "Persian", "Malay", "Tamil"
]

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    # Typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(1)
    # Send greeting and ask language
    keyboard = [
        [InlineKeyboardButton(lang, callback_data=f"lang_{lang}")]
        for lang in LANGUAGES
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Hello {user_first_name}!\n\nPlease select your language:",
        reply_markup=reply_markup
    )

# Language selection callback
async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_lang = query.data.replace("lang_", "")
    # Typing animation
    await context.bot.send_chat_action(chat_id=query.message.chat_id, action="typing")
    await asyncio.sleep(1)
    # Ask for format selection
    keyboard = [
        [
            InlineKeyboardButton("🎵 MP3 (Audio)", callback_data="format_mp3"),
            InlineKeyboardButton("🎥 MP4 (Video)", callback_data="format_mp4")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"✅ Language set to *{selected_lang}*.\n\nNow choose your download format:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# Format selection callback
async def format_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_type = query.data.replace("format_", "")
    context.user_data["format"] = format_type  # store user format
    await context.bot.send_chat_action(chat_id=query.message.chat_id, action="typing")
    await asyncio.sleep(1)
    await query.edit_message_text(
        text=f"🎯 Format set to *{format_type.upper()}*.\n\nNow send me a link from YouTube, Instagram, Twitter or Facebook to download.",
        parse_mode="Markdown"
    )

# Message handler to receive URLs
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_format = context.user_data.get("format", "mp3")
    url = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await asyncio.sleep(1)

    # Placeholder for download logic:
    await update.message.reply_text(
        f"🔗 Got your link: {url}\n\n⚙️ Preparing {user_format.upper()} download..."
    )
    # Here you can plug in your yt-dlp / requests download logic and send file back.

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(language_selected, pattern="^lang_"))
application.add_handler(CallbackQueryHandler(format_selected, pattern="^format_"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

# FastAPI route for Telegram Webhook
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=400)
    return JSONResponse({"status": "ok"})

# Startup event to set webhook automatically
@app.on_event("startup")
async def startup():
    await application.bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook set to {WEBHOOK_URL}")

# Run locally (for testing only)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=8000, reload=True)
