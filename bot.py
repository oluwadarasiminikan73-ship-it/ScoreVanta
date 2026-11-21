import html
import logging
import os
from datetime import datetime, timezone
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sports_api import (
    format_lineup_message,
    get_fixtures,
    get_lineup_text,
    get_live_match_items,
    get_live_scores,
    get_match_analysis,
    get_match_lineups,
    get_match_stats,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

seen_scores: dict[str, tuple[int, int]] = {}
posted_lineups: set[str] = set()
initialized_baseline = False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "⚽ <b>Welcome to ScoreVanta1!</b>\n\n"
        "Lineup announcements first, followed by live goal/score alerts, fixtures, and analysis.\n\n"
        "<b>Commands:</b>\n"
        "/live - Live match scores\n"
        "/fixtures - Today's matches\n"
        "/lineup &lt;match_id&gt; - Starting XI\n"
        "/stats &lt;match_id&gt; - Match snapshot\n"
        "/analysis &lt;match_id&gt; - Form &amp; game analysis"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Fetching live scores...")
    await update.message.reply_text(get_live_scores(), parse_mode=ParseMode.HTML)


async def fixtures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await update.message.reply_text(get_fixtures(today), parse_mode=ParseMode.HTML)


async def lineup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Provide a Match ID. Example: <code>/lineup 701234</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    await update.message.reply_text(get_lineup_text(context.args[0]), parse_mode=ParseMode.HTML)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Provide a Match ID. Example: <code>/stats 701234</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    await update.message.reply_text(get_match_stats(context.args[0]), parse_mode=ParseMode.HTML)


async def analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Provide a Match ID. Example: <code>/analysis 701234</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    await update.message.reply_text(get_match_analysis(context.args[0]), parse_mode=ParseMode.HTML)


async def check_lineups_and_goals(context: ContextTypes.DEFAULT_TYPE) -> None:
    global initialized_baseline

    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID not set; skipping channel check.")
        return

    matches = get_live_match_items()

    # Step 1: Post lineups first whenever rosters become available for a match
    for m in matches:
        mid = m["id"]
        if mid in posted_lineups or m["state"] == "post":
            continue
        lineups = get_match_lineups(mid, m.get("league"))
        if lineups:
            posted_lineups.add(mid)
            if initialized_baseline:
                lineup_msg = format_lineup_message(m, lineups)
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=lineup_msg,
                    parse_mode=ParseMode.HTML,
                )
                logger.info("Posted starting lineup for match %s", mid)

    # Step 2: Baseline scores on first run so we don't replay past goals
    if not initialized_baseline:
        for m in matches:
            seen_scores[m["id"]] = (m["h_score"], m["a_score"])
        initialized_baseline = True
        logger.info("Baseline recorded for %d matches.", len(seen_scores))
        return

    # Step 3: Post goal/score updates after lineups
    for m in matches:
        mid = m["id"]
        if m["state"] not in ("in", "post"):
            continue

        current = (m["h_score"], m["a_score"])
        prev = seen_scores.get(mid)

        if prev is None:
            seen_scores[mid] = current
            if current[0] > 0 or current[1] > 0:
                msg = (
                    f"⚽ <b>SCORE UPDATE!</b> [{html.escape(m['league'])}]\n\n"
                    f"<b>{html.escape(m['home'])}</b> {current[0]} - {current[1]} "
                    f"<b>{html.escape(m['away'])}</b>\n"
                    f"⏱ Status: {html.escape(m['detail'])}"
                )
                await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML)
            continue

        if current != prev:
            seen_scores[mid] = current
            if current[0] > prev[0] or current[1] > prev[1]:
                scorer_side = (
                    f"⚽ Goal for <b>{html.escape(m['home'])}</b>!"
                    if current[0] > prev[0]
                    else f"⚽ Goal for <b>{html.escape(m['away'])}</b>!"
                )
                msg = (
                    f"🚨 <b>GOAL &amp; SCORE UPDATE!</b> [{html.escape(m['league'])}]\n"
                    f"{scorer_side}\n\n"
                    f"<b>{html.escape(m['home'])}</b> {current[0]} - {current[1]} "
                    f"<b>{html.escape(m['away'])}</b>\n"
                    f"⏱ Minute/Status: {html.escape(m['detail'])}"
                )
                await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML)
                logger.info("Posted score update for match %s: %s", mid, current)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("fixtures", fixtures))
    app.add_handler(CommandHandler("lineup", lineup))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("analysis", analysis))
    app.add_error_handler(error_handler)

    app.job_queue.run_repeating(check_lineups_and_goals, interval=120, first=10)

    logger.info("ScoreVanta1 running (lineups first, then score updates)...")
    app.run_polling()
