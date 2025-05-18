import os
import json
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load Telegram token from environment
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not set in environment.")

# Your local 'db.json' file (auto-created if not exists)
DB_PATH = "db.json"

# Ensure database file exists
if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump({}, f)

# Load or save DB
def load_db():
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = f"""👋 Hi {user.first_name}!

Welcome to your *Guangzhou Trip Assistant* 🇨🇳✨

You can use this bot to save and organize your favorite:
📹 TikTok or Xiaohongshu food spots
🛍️ Shops
📍 Attractions

Here’s how to use me:

1️⃣ Paste any *TikTok* or *Xiaohongshu* link.
2️⃣ I’ll ask you to choose a category (e.g. Food, Shopping, etc).
3️⃣ Use /view to see all saved links.
4️⃣ Use /search <keyword> to filter by keyword.

Let’s start! Paste your first link 👇
"""
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    url = update.message.text.strip()

    if not ("tiktok.com" in url or "xiaohongshu.com" in url):
        await update.message.reply_text("❌ Please send a valid TikTok or Xiaohongshu link.")
        return

    context.user_data["pending_url"] = url

    # Ask for category
    keyboard = [
        [InlineKeyboardButton("🍜 Food", callback_data="cat:Food")],
        [InlineKeyboardButton("🛍 Shopping", callback_data="cat:Shopping")],
        [InlineKeyboardButton("📍 Attractions", callback_data="cat:Attractions")],
    ]
    await update.message.reply_text(
        "What category does this link belong to?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    category = query.data.split(":")[1]
    url = context.user_data.get("pending_url")

    if not url:
        await query.edit_message_text("❌ No link to save. Please send a new link.")
        return

    db = load_db()
    user_entries = db.get(user_id, [])
    user_entries.append({"url": url, "category": category})
    db[user_id] = user_entries
    save_db(db)

    await query.edit_message_text(f"✅ Saved to *{category}*!", parse_mode="Markdown")

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    entries = db.get(user_id, [])

    if not entries:
        await update.message.reply_text("You haven’t saved anything yet. Send a TikTok or Xiaohongshu link!")
        return

    message = "📚 *Your Saved Links:*\n\n"
    for entry in entries:
        message += f"• [{entry['category']}] {entry['url']}\n"

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    entries = db.get(user_id, [])

    if len(context.args) == 0:
        await update.message.reply_text("Please provide a keyword, e.g. `/search dumpling`", parse_mode="Markdown")
        return

    keyword = " ".join(context.args).lower()
    results = [e for e in entries if keyword in e['url'].lower() or keyword in e['category'].lower()]

    if not results:
        await update.message.reply_text("❌ No results found.")
        return

    message = f"🔍 *Search results for:* `{keyword}`\n\n"
    for entry in results:
        message += f"• [{entry['category']}] {entry['url']}\n"

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

# --- Main App Setup ---

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(handle_category, pattern=r'^cat:'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
