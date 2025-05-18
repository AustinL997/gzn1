import os
import json
import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# === Setup Logging ===
logging.basicConfig(level=logging.INFO)

# === Load Token from Environment ===
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not set in environment")

# === Load or Initialize JSON Database ===
DB_FILE = "db.json"
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        video_db = json.load(f)
else:
    video_db = {}

# === /start Command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to @gzn1_bot!\n\n"
        "Use the buttons below to get started:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Video", callback_data="add_video")],
            [InlineKeyboardButton("📋 List Videos", callback_data="list_videos")],
            [InlineKeyboardButton("🔍 Search by Hashtag", callback_data="search_hashtag")]
        ])
    )

# === Handle Callback Buttons ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_video":
        context.user_data["mode"] = "add"
        await query.message.reply_text("📎 Please send me a TikTok or Xiaohongshu video link with optional hashtags.\n\nExample:\nhttps://www.tiktok.com/... #food #hotpot")
    elif query.data == "list_videos":
        user_id = str(query.from_user.id)
        videos = video_db.get(user_id, [])
        if not videos:
            await query.message.reply_text("You haven’t saved any videos yet!")
        else:
            reply = "\n\n".join(f"{idx+1}. {v['url']} {' '.join(v['hashtags'])}" for idx, v in enumerate(videos))
            await query.message.reply_text("📋 Your videos:\n\n" + reply)
    elif query.data == "search_hashtag":
        context.user_data["mode"] = "search"
        await query.message.reply_text("🔍 Send me a hashtag to search (e.g., #food or #togo)")

# === Handle Messages ===
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message = update.message.text.strip()
    mode = context.user_data.get("mode")

    if mode == "add":
        url = message.split()[0]
        hashtags = [word for word in message.split() if word.startswith("#")]
        if not url.startswith("http"):
            await update.message.reply_text("⚠️ Please include a valid video link.")
            return

        video_db.setdefault(user_id, []).append({"url": url, "hashtags": hashtags})
        with open(DB_FILE, "w") as f:
            json.dump(video_db, f)

        await update.message.reply_text("✅ Video saved!\n\nUse /start to add or search again.")
        context.user_data["mode"] = None

    elif mode == "search":
        tag = message.lower()
        found = []
        for entry in video_db.get(user_id, []):
            if tag in (h.lower() for h in entry.get("hashtags", [])):
                found.append(entry)

        if not found:
            await update.message.reply_text("❌ No videos found with that hashtag.")
        else:
            reply = "\n\n".join(f"{v['url']} {' '.join(v['hashtags'])}" for v in found)
            await update.message.reply_text(f"🔍 Results for {tag}:\n\n" + reply)

        context.user_data["mode"] = None
    else:
        await update.message.reply_text("❓ Please use /start and choose an option.")

# === Run Bot in Background Thread ===
def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

# === Dummy Web Server to Bind Port ===
def run_web_server():
    dummy_app = Flask(__name__)

    @dummy_app.route('/')
    def home():
        return "✅ Bot is alive!"

    port = int(os.environ.get("PORT", 5000))
    dummy_app.run(host="0.0.0.0", port=port)

# === Run Both in Parallel ===
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    run_web_server()
