import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)
HELP = (
    "/start — introduction\n/help — help\n/whoami — your Telegram ID\n\n"
    "/today — today's events\n/tomorrow — tomorrow's events\n/week — next seven calendar days\n"
    "/add Title | YYYY-MM-DD HH:MM | minutes\n/delete search words\n\n"
    "/play song or artist — YouTube search link\n/youtube topic — YouTube search link\n\n"
    "Calendar changes require confirmation. Dates use BOT_TIMEZONE (default Asia/Singapore). "
    "You can also type 'play relaxing piano'. Send a voice recording (up to 60 seconds) "
    "for calendar or YouTube requests after configuring voice. Other text is echoed."
)


def private_message(update):
    return bool(update.effective_chat and update.effective_chat.type == "private"
                and update.effective_user and update.effective_message)


async def authorized(update, context):
    if not private_message(update):
        return False
    owner = context.bot_data["allowed_user_id"]
    if owner is None:
        await update.effective_message.reply_text(
            "Setup mode: only /whoami is available. Set TELEGRAM_ALLOWED_USER_ID in .env and restart."
        )
        return False
    if update.effective_user.id != owner:
        await update.effective_message.reply_text("This is a private bot. Access denied.")
        return False
    return True


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_message(update):
        return
    owner = context.bot_data["allowed_user_id"]
    if owner is not None and update.effective_user.id != owner:
        await update.effective_message.reply_text("This is a private bot. Access denied.")
        return
    await update.effective_message.reply_text(
        f"Your Telegram user ID: {update.effective_user.id}\n"
        "Set this number as TELEGRAM_ALLOWED_USER_ID in .env, then restart."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await authorized(update, context):
        await update.effective_message.reply_text("Talking Bot is connected!\n\n" + HELP)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await authorized(update, context):
        await update.effective_message.reply_text(HELP)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await authorized(update, context):
        from .youtube import reply_search, text_request
        query = text_request(update.effective_message.text or "")
        if query is not None:
            await reply_search(update.effective_message, query)
            return
        # Bound UTF-16 units so emoji also fit Telegram's message length limit.
        value = (update.effective_message.text or "").encode("utf-16-le")
        value = value[:8000].decode("utf-16-le", errors="ignore")
        await update.effective_message.reply_text("You said: " + value)


async def unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await authorized(update, context):
        await update.effective_message.reply_text("Please send text, a voice recording, or use /help.")


async def on_error(update, context):
    # Do not log exception text, URLs containing tokens, or message contents.
    logger.error("Telegram update failed (%s).", type(context.error).__name__)


def build_application(settings):
    from .calendar_handlers import calendar_callback, calendar_command
    from .youtube import youtube_command
    from .voice import voice_message
    app = Application.builder().token(settings.token).build()
    app.bot_data["allowed_user_id"] = settings.allowed_user_id
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["play", "youtube"], youtube_command))
    app.add_handler(CommandHandler(["today", "tomorrow", "week", "add", "delete"], calendar_command))
    app.add_handler(CallbackQueryHandler(calendar_callback, pattern=r"^cal:(confirm|cancel|select):[a-f0-9]{16}$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_handler(MessageHandler(filters.ALL, unsupported))
    app.add_error_handler(on_error)
    return app
