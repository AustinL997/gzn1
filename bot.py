import os
import asyncio
import json
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

# === Video Storage (now includes hashtags) ===
DB_FILE = "db.json"
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        video_storage = json.load(f)
else:
    video_storage = []

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I'm your Guangzhou trip assistant.\n\n"
        "Here are some commands you can try:\n"
        "/addvideo - Add a new video to your itinerary\n"
        "/list - List all saved videos\n"
        "/search - Search videos by hashtag (e.g., #food)\n"
        "/help - Get help instructions"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Instructions:\n"
        "1. Use /addvideo to add a video link. After this command, send me the video URL with optional hashtags.\n"
        "   Example: https://www.tiktok.com/... #food #hotpot\n"
        "2. Use /list to see your saved videos.\n"
        "3. Use /search to find videos by hashtag.\n"
        "4. Use /start to see the main menu anytime."
    )

async def addvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please send me the video URL you want to add, with optional hashtags.\nExample: https://www.tiktok.com/... #food #togo"
    )
    context.user_data['expecting_video'] = True

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not video_storage:
        await update.message.reply_text("No videos saved yet. Use /addvideo to add some.")
    else:
        videos_text = "\n\n".join(f"{idx+1}. {item['url']} {' '.join(item['hashtags'])}" for idx, item in enumerate(video_storage))
        await update.message.reply_text(f"Here are your saved videos:\n\n{videos_text}")
    await update.message.reply_text("You can add more videos with /addvideo or get help with /help.")

async def search_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a hashtag to search (e.g., #food, #togo, #tobuy).")
    context.user_data['expecting_search'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if context.user_data.get('expecting_video'):
        if text.startswith("http"):
            url = text.split()[0]
            hashtags = [word for word in text.split() if word.startswith("#")]
            video_storage.append({"url": url, "hashtags": hashtags})
            with open(DB_FILE, "w") as f:
                json.dump(video_storage, f)
            await update.message.reply_text("✅ Video added successfully! Use /list to view or /search to find by hashtag.")
        else:
            await update.message.reply_text("❌ That doesn't look like a valid URL. Please send a correct video link.")
        context.user_data['expecting_video'] = False

    elif context.user_data.get('expecting_search'):
        tag = text.lower()
        results = [v for v in video_storage if tag in [h.lower() for h in v.get("hashtags", [])]]
        if not results:
            await update.message.reply_text("❌ No videos found with that hashtag.")
        else:
            reply = "\n\n".join(f"{v['url']} {' '.join(v['hashtags'])}" for v in results)
            await update.message.reply_text(f"🔍 Results for {tag}:\n\n{reply}")
        context.user_data['expecting_search'] = False

    else:
        await update.message.reply_text(f"Received: {text}\nUse /help for instructions.")

# === Minimal HTTP server for Render ===
async def handle_root(request):
    return web.Response(text="Telegram bot is running.")

async def run_web_app():
    app = web.Application()
    app.add_routes([web.get('/', handle_root)])

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# === Main Async Entry ===
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addvideo", addvideo))
    app.add_handler(CommandHandler("list", list_videos))
    app.add_handler(CommandHandler("search", search_videos))
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
