import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

DB_FILE = "db.json"

def load_data():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"videos": []}

def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! 👋 Send a TikTok link with hashtags like #food or #shopping to save it.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user.username or str(update.effective_user.id)

    if "tiktok.com" in text:
        tags = [w.strip("#") for w in text.split() if w.startswith("#")]
        entry = {
            "url": text,
            "tags": tags,
            "user": user
        }
        data = load_data()
        data["videos"].append(entry)
        save_data(data)
        await update.message.reply_text(f"✅ Saved TikTok with tags: {', '.join(tags)}")
    else:
        await update.message.reply_text("❗ Please send a TikTok link with hashtags (e.g. #food, #shopping)")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        keyword = context.args[0].lower()
        data = load_data()
        matches = [
            v["url"] for v in data["videos"]
            if keyword in [t.lower() for t in v["tags"]]
        ]
        if matches:
            await update.message.reply_text("🔍 Results:\n" + "\n".join(matches))
        else:
            await update.message.reply_text("❌ No matches found.")
    else:
        await update.message.reply_text("Usage: /search <keyword>")

BOT_TOKEN = os.getenv("BOT_TOKEN")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("search", search))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

import asyncio

async def main():
    print("🚀 Bot is running on Render...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
