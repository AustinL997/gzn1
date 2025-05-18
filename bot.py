async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    bot = context.bot

    # Delete the command message if possible
    try:
        await bot.delete_message(chat_id=chat.id, message_id=update.message.message_id)
    except Exception as e:
        logging.warning(f"Failed to delete command message: {e}")

    # Fetch recent messages sent by the bot
    try:
        async for message in bot.get_chat_history(chat_id=chat.id, limit=100):
            if message.from_user and message.from_user.id == bot.id:
                try:
                    await bot.delete_message(chat_id=chat.id, message_id=message.message_id)
                except Exception as e:
                    logging.warning(f"Failed to delete message {message.message_id}: {e}")
    except Exception as e:
        logging.warning(f"Failed to fetch chat history: {e}")

    # Send a confirmation message
    confirmation = await update.message.reply_text("🔄 Bot messages have been cleared from the chat.")

    # Optionally delete the confirmation message after a short delay
    await asyncio.sleep(5)
    try:
        await confirmation.delete()
    except Exception as e:
        logging.warning(f"Failed to delete confirmation message: {e}")
