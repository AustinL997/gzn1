import json
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from datetime import datetime
import asyncio
from aiohttp import web

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "db.json"

# Utility functions
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

# Bot handlers
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Send me a TikTok link with optional tags or notes. Example:\n"
        "https://www.tiktok.com/@user/video/1234567890\n"
        "Tags: #food #dessert\n"
        "Note: Looks tasty!"
    )

async def handle_message(update: Update, context: CallbackContext):
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

async def list_entries(update: Update, context: CallbackContext):
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

async def view_entry(update: Update, context: CallbackContext):
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

# HTTP server handler for health checks
async def handle_health(request):
    return web.Response(text="OK")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_entries))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(view_entry))

    # Create aiohttp web server app for Render health checks
    web_app = web.Application()
    web_app.router.add_get('/health', handle_health)

    # Get port from environment (Render uses PORT env var)
    port = int(os.environ.get("PORT", 8080))

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logging.info(f"HTTP server started on port {port}")

    # Start Telegram bot polling (non-blocking)
    await app.start()
    logging.info("Telegram bot started polling...")

    # Run forever to keep the server and bot alive
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.stop()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
