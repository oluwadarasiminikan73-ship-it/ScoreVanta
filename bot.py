import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sports_api import get_live_scores, get_fixtures, get_match_analysis

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚽ **Welcome to ScoreVanta1!**\n\n"
        "Your hub for live scores, updates, fixtures, stats, and game analysis.\n\n"
        "**Commands:**\n"
        "/live - Live match scores & updates\n"
        "/fixtures - Today's upcoming matches\n"
        "/analysis <match_id> - Stats & game analysis"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching live scores...")
    data = get_live_scores()
    await update.message.reply_text(data, parse_mode="Markdown")

async def fixtures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = get_fixtures(today)
    await update.message.reply_text(data, parse_mode="Markdown")

async def analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a Match ID. Example: `/analysis 123456`", parse_mode="Markdown")
        return
    data = get_match_analysis(context.args[0])
    await update.message.reply_text(data, parse_mode="Markdown")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("fixtures", fixtures))
    app.add_handler(CommandHandler("analysis", analysis))
    
    print("ScoreVanta1 is running...")
    app.run_polling()
