import logging
import os
from datetime import datetime, timezone
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sports_api import (
    get_fixtures,
    get_live_scores,
    get_match_analysis,
    get_match_stats,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "⚽ <b>Welcome to ScoreVanta1!</b>\n\n"
        "Delivering live scores, match updates, fixtures, statistics, and insightful game analysis.\n\n"
        "<b>Commands:</b>\n"
        "/live - Live match scores &amp; IDs\n"
        "/fixtures - Today's matches &amp; IDs\n"
        "/stats &lt;match_id&gt; - Match statistics\n"
        "/analysis &lt;match_id&gt; - Pre-match analysis &amp; probabilities"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Fetching live scores...")
    await update.message.reply_text(get_live_scores(), parse_mode=ParseMode.HTML)


async def fixtures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await update.message.reply_text(get_fixtures(today), parse_mode=ParseMode.HTML)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Provide a Match ID. Example: <code>/stats 123456</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    await update.message.reply_text(get_match_stats(context.args[0]), parse_mode=ParseMode.HTML)


async def analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Provide a Match ID. Example: <code>/analysis 123456</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    await update.message.reply_text(get_match_analysis(context.args[0]), parse_mode=ParseMode.HTML)


async def post_channel_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID not set; skipping 5-minute channel post.")
        return

    report = get_live_scores()
    if report == "No live matches right now." or report.startswith("⚠️"):
        logger.info("No live match update posted to %s: %s", CHANNEL_ID, report)
        return

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=report,
        parse_mode=ParseMode.HTML,
    )
    logger.info("Published 5-minute update to channel %s", CHANNEL_ID)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("fixtures", fixtures))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("analysis", analysis))
    app.add_error_handler(error_handler)

    app.job_queue.run_repeating(post_channel_update, interval=300, first=15)

    logger.info("ScoreVanta1 started; posting to channel every 5 minutes.")
    app.run_polling()
