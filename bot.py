import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not set in environment")

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I'm your Guangzhou trip assistant.\n"
        "Use /addvideo to add videos.\n"
        "Use /list to see saved videos.\n"
        "Use /help to get instructions."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Received: {update.message.text}")

# Minimal HTTP handler for Render port requirement
async def handle_root(request):
    return web.Response(text="Telegram bot is running.")

async def run_web_app():
    app = web.Application()
    app.add_routes([web.get('/', handle_root)])

    port = int(os.environ.get("PORT", 10000))  # Render assigns $PORT
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    # Build Telegram bot application
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Initialize Telegram bot app (connect to Telegram servers)
    await app.initialize()
    # Start the bot (but not polling yet)
    await app.start()
    # Start polling for updates
    await app.updater.start_polling()

    # Start web server concurrently
    await run_web_app()

    # Now just wait forever (or until cancelled)
    await asyncio.Event().wait()

    # Cleanup on shutdown (optional, if you ever cancel)
    await app.updater.stop_polling()
    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
