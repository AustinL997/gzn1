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
        data = json.load(f)
        video_storage = data.get("videos", [])
else:
    video_storage = []

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I'm your Guangzhou trip assistant.\n\n"
        "Here are some commands you can try:\n"
        "/addvideo - Add a new video to your itinerary\n"
        "/list - List all saved videos\n"
        "/search - Search videos by hashtags (e.g., /search #food #hotpot)\n"
        "/deletevideo - Delete a video by its number (e.g., /deletevideo 2)\n"
        "/editvideo - Edit a video by its number (e.g., /editvideo 3)\n"
        "/clear - Clear bot messages from the chat\n"
        "/help - Get help instructions"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Instructions:\n"
        "1. Use /addvideo to add a video link. After this command, send me the video URL with optional hashtags.\n"
        "   Example: https://www.tiktok.com/... #food #hotpot\n"
        "2. Use /list to see your saved videos.\n"
        "3. Use /search followed by hashtags to find videos. Example: /search #food #hotpot\n"
        "4. Use /deletevideo followed by the video number to delete. Example: /deletevideo 2\n"
        "5. Use /editvideo followed by the video number to edit. Example: /editvideo 3\n"
        "6. Use /clear to delete bot messages from the chat.\n"
        "7. Use /start to see the main menu anytime."
    )

async def addvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please send me the video URL you want to add, with optional hashtags.\nExample: https://www.tiktok.com/... #food #hotpot"
    )
    context.user_data['expecting_video'] = True

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not video_storage:
        await update.message.reply_text("No videos saved yet. Use /addvideo to add some.")
    else:
        # Segmentation logic
        segmented_videos = {}
        for video in video_storage:
            # First level: by city
            city_tag = next((tag for tag in video.get("hashtags", []) if tag.lower() in ["#gz", "#sz"]), None)
            if not city_tag:
                continue
            city = city_tag.lower().strip("#")
            # Second level: by category
            category_tags = ["#toexplore", "#toeat", "#tobuy"]
            category = next((tag for tag in video.get("hashtags", []) if tag.lower() in category_tags), None)
            if not category:
                continue
            category = category.lower().strip("#")
            # Third level: by similar tags
            similar_tags = [tag for tag in video.get("hashtags", []) if tag.lower() != city_tag.lower() and tag.lower() != category]
            similar_tags.sort()
            # Organize into dictionary
            if city not in segmented_videos:
                segmented_videos[city] = {}
            if category not in segmented_videos[city]:
                segmented_videos[city][category] = {}
            for tag in similar_tags:
                if tag not in segmented_videos[city][category]:
                    segmented_videos[city][category][tag] = []
                segmented_videos[city][category][tag].append(video)

        # Format the response
        response = ""
        for city, categories in segmented_videos.items():
            response += f"\n📍 {city.upper()}"
            for category, tags in categories.items():
                response += f"\n  - {category.capitalize()}"
                for tag, videos in tags.items():
                    response += f"\n    * {tag.capitalize()}:"
                    for video in videos:
                        response += f"\n      - {video['url']} {' '.join(video.get('hashtags', []))}"
        if not response:
            response = "No videos found matching the segmentation criteria."
        await update.message.reply_text(response)

async def search_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Please provide at least one hashtag to search. Example: /search #food #hotpot")
        return

    search_tags = [tag.lower() for tag in args if tag.startswith("#")]
    if not search_tags:
        await update.message.reply_text("Please provide valid hashtags starting with '#'.")
        return

    results = []
    for video in video_storage:
        video_tags = [h.lower() for h in video.get("hashtags", [])]
        if all(tag in video_tags for tag in search_tags):
            results.append(video)

    if not results:
        await update.message.reply_text("No videos found with the specified hashtags.")
    else:
        reply = "\n\n".join(f"{v['url']} {' '.join(v['hashtags'])}" for v in results)
        await update.message.reply_text(f"Results for {' '.join(search_tags)}:\n\n{reply}")

async def deletevideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Please provide the video number to delete. Example: /deletevideo 2")
        return

    index = int(args[0]) - 1
    if 0 <= index < len(video_storage):
        removed_video = video_storage.pop(index)
        with open(DB_FILE, "w") as f:
            json.dump({"videos": video_storage}, f, indent=2)
        await update.message.reply_text(f"✅ Removed video: {removed_video['url']}")
    else:
        await update.message.reply_text("❌ Invalid video number. Use /list to see available videos.")

async def editvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Please provide the video number to edit. Example: /editvideo 3")
        return

    index = int(args[0]) - 1
    if 0 <= index < len(video_storage):
        context.user_data['editing_video_index'] = index
        await update.message.reply_text(
            f"Please send the new video URL and hashtags for video {index + 1}.\nExample: https://www.tiktok.com/... #newtag"
        )
    else:
        await update.message.reply_text("❌ Invalid video number. Use /list to see available videos.")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    bot = context.bot

    async for message in bot.get_chat_history(chat_id=chat.id, limit=100):
        if message.from_user and message.from_user.id == bot.id:
            try:
                await bot.delete_message(chat_id=chat.id, message_id=message.message_id)
            except Exception as e:
                logging.warning(f"Failed to delete message {message.message_id}: {e}")

    await update.message.reply_text("Bot messages have been cleared from the chat.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if context.user_data.get('expecting_video'):
        if text.startswith("http"):
            url = text.split()[0]
            hashtags = [word for word in text.split() if word.startswith("#")]
            video_storage.append({"url": url, "hashtags": hashtags})
            with open(DB_FILE, "w") as f:
                json.dump({"videos": video_storage}, f, indent=2)
            await update.message.reply_text("✅ Video added successfully! Use /list to view or /search to find by hashtag.")
        else:
            await update.message.reply_text("❌ That doesn't look like a valid URL. Please send a correct video link.")
        context.user_data['expecting_video'] = False
    elif 'editing_video_index' in context.user_data:
        index = context.user_data['editing_video_index']
        if text.startswith("http"):
            url = text.split()[0]
            hashtags = [word for word in text.split() if word.startswith("#")]
            video_storage[index] = {"url": url, "hashtags": hashtags}
            with open(DB_FILE, "w") as f:
                json.dump({"videos": video_storage}, f, indent=2)
            await update.message.reply_text(f"✅ Video {index + 1} updated successfully!")
        else:
            await update.message.reply_text("❌ That doesn't look like a valid URL. Please send a correct video link.")
        del context.user_data['editing_video_index']
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

    app.add_handler
::contentReference[oaicite:0]{index=0}
 
