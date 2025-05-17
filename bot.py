import json
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "db.json"

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
        data[user_id] = {"entries": []}

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
        [InlineKeyboardButton(f"Item {i + 1}", callback_data=f"view_{i}")]
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
        text = f"📌 TikTok #{index + 1}\n{entry['url']}\n🕒 {entry['timestamp']}"
        await query.edit_message_text(text)
    except IndexError:
        await query.edit_message_text("Invalid entry.")

async def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_entries))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(view_entry))

    logger.info("Bot started polling...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
