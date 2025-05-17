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

# Utility functions unchanged...

# Handlers unchanged...

async def start(update: Update, context: CallbackContext):
    # your handler code unchanged

async def handle_message(update: Update, context: CallbackContext):
    # your handler code unchanged

async def list_entries(update: Update, context: CallbackContext):
    # your handler code unchanged

async def view_entry(update: Update, context: CallbackContext):
    # your handler code unchanged

# New: aiohttp handler for Render health checks
async def handle_health(request):
    return web.Response(text="OK")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_entries))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(view_entry))

    # Create aiohttp web server app
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

    # Run forever
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.stop()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
