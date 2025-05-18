import os
import json
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not set in environment")

DB_PATH = "db.json"

# Ensure db.json exists
if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump({}, f)

def load_db():
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = f"""👋 Hi {user.first_name}!

Welcome to your *Guangzhou Trip Assistant* 🇨🇳✨

You can save your favorite TikTok and Xiaohongshu links for:
🍜 Food
🛍 Shopping
📍 Attractions

How to use me:
1️⃣ Send me a TikTok or Xiaohongshu link.
2️⃣ Choose the category when prompted.
3️⃣ Use /view to see saved links.
4️⃣ Use /search <keyword> to filter saved links.

Send your first link now!"""
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # Check if it's a TikTok or Xiaohongshu link
    if "tiktok.com" in text or "xiaohongshu.com" in text:
        context.user_data["pending_url"] = text
        keyboard = [
            [InlineKeyboardButton("🍜 Food", callback_data="cat:Food")],
            [InlineKeyboardButton("🛍 Shopping", callback_data="cat:Shopping")],
            [InlineKeyboardButton("📍 Attractions", callback_data="cat:Attractions")],
        ]
        await update.message.reply_text(
            "Which category does this link belong to?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Simple echo for other texts
        await update.message.reply_text(f"Received: {text}")

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    category = query.data.split(":")[1]
    url = context.user_data.get("pending_url")

    if not url:
        await query.edit_message_text("❌ No link found. Please send a new TikTok or Xiaohongshu link.")
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
        await update.message.reply_text("You have no saved links yet. Send me a TikTok or Xiaohongshu link!")
        return

    message = "📚 *Your Saved Links:*\n\n"
    for entry in entries:
        message += f"• [{entry['category']}] {entry['url']}\n"

    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    entries = db.get(user_id, [])

    if not context.args:
        await update.message.reply_text("Please provide a keyword after /search, e.g. `/search dumpling`", parse_mode="Markdown")
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

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(handle_category, pattern=r"^cat:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Bot started polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
