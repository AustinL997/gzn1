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

# In-memory storage for example
video_storage = []

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I'm your Guangzhou trip assistant.\n\n"
        "Here are some commands you can try:\n"
        "/addvideo - Add a new video to your itinerary\n"
        "/list - List all saved videos\n"
        "/help - Get help instructions"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Instructions:\n"
        "1. Use /addvideo to add a video link. After this command, send me the video URL.\n"
        "2. Use /list to see your saved videos.\n"
        "3. Use /start to see the main menu anytime."
    )

async def addvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please send me the video URL you want to add."
    )
    # Set user state to expect the next message as video URL
    context.user_data['expecting_video'] = True

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not video_storage:
        await update.message.reply_text("No videos saved yet. Use /addvideo to add some.")
    else:
        videos_text = "\n".join(f"{idx+1}. {url}" for idx, url in enumerate(video_storage))
        await update.message.reply_text(f"Here are your saved videos:\n{videos_text}")
    await update.message.reply_text("You can add more videos with /addvideo or get help with /help.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if expecting a video URL after /addvideo
    if context.user_data.get('expecting_video'):
        video_url = update.message.text.strip()
        # Simple validation (can be improved)
        if video_url.startswith("http"):
            video_storage.append(video_url)
            await update.message.reply_text(f"Video added successfully!\nYou can add another one or type /list to see all.")
        else:
            await update.message.reply_text("That doesn't look like a valid URL. Please send a valid video URL.")
        # Reset state
        context.user_data['expecting_video'] = False
    else:
        await update.message.reply_text(f"Received: {update.message.text}\nUse /help for instructions.")

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
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addvideo", addvideo))
    app.add_handler(CommandHandler("list", list_videos))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await run_web_app()

    await asyncio.Event().wait()

    await app.updater.stop_polling()
    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
