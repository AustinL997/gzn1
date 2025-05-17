import json
import os
import logging
from datetime import datetime

from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import uvicorn
import nest_asyncio
import asyncio

# Fix for nested event loops (e.g. Render)
nest_asyncio.apply()

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

DB_FILE = "db.json"

# Telegram Bot instance for webhook commands
bot = Bot(token=BOT_TOKEN)

# FastAPI app instance
app = FastAPI()

# Load/save data utils
def load_data():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def ensure_user(data, user_id):
    if user_id not in data:
        data[user_id] = {
            "entries": [],
        }

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a TikTok link with optional tags or notes. Example:\n"
        "https://www.tiktok.com/@user/video/1234567890\n"
        "Tags: #food #dessert\n"
        "Note: Looks tasty!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if "tiktok.com" not in text:
        await update.message.reply_text("Please send a valid TikTok link.")
        return

    data = load_data()
    ensure_user(data, user_id)

    entry = {
        "url": text,
        "timestamp": datetime.now().isoformat(),
    }
    data[user_id]["entries"].append(entry)
    save_data(data)

    await update.message.reply_text("Saved your TikTok!")

async def list_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]["entries"]:
        await update.message.reply_text("You haven't saved any TikToks yet.")
        return

    keyboard = [
        [InlineKeyboardButton(f"Item {i+1}", callback_data=f"view_{i}")]
        for i in range(len(data[user_id]["entries"]))
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Select an item to view:", reply_markup=reply_markup)

async def view_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    index = int(query.data.split("_")[1])
    data = load_data()

    try:
        entry = data[user_id]["entries"][index]
        text = f"📌 TikTok #{index+1}\n{entry['url']}\n🕒 {entry['timestamp']}"
        await query.edit_message_text(text)
    except IndexError:
        await query.edit_message_text("Invalid entry.")

async def setwebhook_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /setwebhook <your_public_url>\n"
            "Example: /setwebhook https://yourdomain.com"
        )
        return

    public_url = context.args[0].rstrip("/")
    webhook_url = f"{public_url}/webhook/{BOT_TOKEN}"

    success = await bot.set_webhook(webhook_url)
    if success:
        await update.message.reply_text(f"Webhook successfully set to:\n{webhook_url}")
    else:
        await update.message.reply_text("Failed to set webhook. Check the URL and try again.")

# Build telegram application (handlers)
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("list", list_entries))
application.add_handler(CommandHandler("setwebhook", setwebhook_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(view_entry))

# FastAPI route for Telegram webhook
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """Telegram will POST updates here"""
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    await application.update_queue.put(update)  # Push update to telegram.ext Application
    return Response(status_code=200)

# Optional root endpoint to verify server is running
@app.get("/")
async def root():
    return {"status": "Bot is running"}

# Start the application with uvicorn (useful for local testing)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting bot on port {port}")
    uvicorn.run("bot:app", host="0.0.0.0", port=port, log_level="info")


