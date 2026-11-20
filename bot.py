import logging
import os
from datetime import datetime, timezone
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sports_api import get_live_scores, get_fixtures, get_match_analysis

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = (
        "⚽ <b>Welcome to ScoreVanta1!</b>\n\n"
        "Delivering live scores, match updates, fixtures, statistics, and insightful game analysis to keep you ahead of every match.\n\n"
        "<b>Commands:</b>\n"
        "/live - Live match scores &amp; updates\n"
        "/fixtures - Today's upcoming matches\n"
        "/analysis &lt;match_id&gt; - Stats &amp; game analysis"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Fetching live scores...")
    data = get_live_scores()
    await update.message.reply_text(data, parse_mode=ParseMode.HTML)


async def fixtures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = get_fixtures(today)
    await update.message.reply_text(data, parse_mode=ParseMode.HTML)


async def analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Please provide a Match ID. Example: <code>/analysis 123456</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    data = get_match_analysis(context.args[0])
    await update.message.reply_text(data, parse_mode=ParseMode.HTML)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("fixtures", fixtures))
    app.add_handler(CommandHandler("analysis", analysis))
    app.add_error_handler(error_handler)

    logger.info("ScoreVanta1 is running...")
    app.run_polling()
