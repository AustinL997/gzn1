import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
DB_FILE = "db.json"

if not TOKEN:
    raise ValueError("TOKEN not set in environment")

# Load or initialize database
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Add Video", callback_data="add")],
        [InlineKeyboardButton("📄 List All Videos", callback_data="list")]
    ]
    await update.message.reply_text(
        "👋 Welcome to the Guangzhou trip bot!\n\nYou can:\n- Add videos with hashtags (e.g. #food, #togo)\n- List all saved videos\n- Search by sending a hashtag (e.g. #hotpot)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Handle button actions
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    context.user_data["awaiting_input"] = query.data

    if query.data == "add":
        await query.message.reply_text("📎 Send the video link and include hashtags (e.g. https://tiktok.com/... #food #hotpot)")
    elif query.data == "list":
        db = load_db()
        messages = []
        for uid, items in db.items():
            for item in items:
                tags = " ".join(item.get("hashtags", []))
                messages.append(f"{item['url']} {tags}")
        if messages:
            await query.message.reply_text("\n\n".join(messages[:20]))  # show max 20 results
        else:
            await query.message.reply_text("No videos saved yet!")

# Add videos with hashtags
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()
    db = load_db()

    if context.user_data.get("awaiting_input") == "add":
        if "http" not in text:
            await update.message.reply_text("⚠️ Please include a valid link starting with http")
            return

        hashtags = [word for word in text.split() if word.startswith("#")]
        video_url = text.split()[0]

        if user_id not in db:
            db[user_id] = []
        db[user_id].append({
            "url": video_url,
            "hashtags": hashtags
        })
        save_db(db)

        await update.message.reply_text("✅ Video saved!\nYou can now search using hashtags like #food or #togo.")
        context.user_data["awaiting_input"] = None
    else:
        # Hashtag search
        if text.startswith("#"):
            db = load_db()
            results = []
            for items in db.values():
                for item in items:
                    if text in item.get("hashtags", []):
                        results.append(f"{item['url']} {' '.join(item['hashtags'])}")
            if results:
                await update.message.reply_text("\n\n".join(results[:20]))
            else:
                await update.message.reply_text("❌ No results found for that hashtag.")
        else:
            await update.message.reply_text("🤖 Please use the menu or type a hashtag (e.g. #food) to search.")

# Main
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
