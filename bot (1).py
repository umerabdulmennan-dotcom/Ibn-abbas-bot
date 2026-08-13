"""
IBN ABBAS QURAN CENTER - HARA TOWN
Telegram Bot: @Abuki07_bot

Features:
1. Auto-reply to common questions (keyword based)
2. AI Q&A about Islam (using Anthropic Claude API)
3. Scheduled daily posts (Hadith/Ayah) to the channel
4. Broadcast command for the admin
5. Welcome message for new members

Deploy on Railway.app / Render.com
"""

import os
import logging
import random
from datetime import time as dtime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import anthropic

# ------------------------------------------------------------------
# CONFIGURATION  (set these as Environment Variables on your host)
# ------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")                 # from BotFather
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")  # from console.anthropic.com
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@ibnuabbas_hara")  # your channel
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
POST_HOUR_UTC = int(os.environ.get("POST_HOUR_UTC", "3"))   # UTC hour for daily post (3 UTC = 6 AM Addis)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# AUTO-REPLY: keyword -> response  (edit / add freely)
# ------------------------------------------------------------------
AUTO_REPLIES = {
    "ሰላም": "ወዓለይኩም ሰላም! 🕌 ወደ IBN ABBAS QURAN CENTER - HARA TOWN እንኳን በደህና መጡ። ጥያቄ ካለዎት ይላኩ።",
    "ቻናል": f"የቻናላችን ሊንክ፦ {CHANNEL_USERNAME}",
    "ሰዓት": "የሶላት ሰዓት ለማወቅ አካባቢዎን ይላኩልኝ ወይም local mosque schedule ይመልከቱ።",
    "ማዕከል": "IBN ABBAS QURAN CENTER HARA TOWN የቁርአን እና እስልምና ትምህርት ማዕከል ነው። ለበለጠ መረጃ ቻናላችንን ይከተሉ።",
}

WELCOME_TEXT = (
    "🕌 እንኳን ደህና መጡ!\n\n"
    "ወደ *IBN ABBAS QURAN CENTER - HARA TOWN* ቦት በደህና መጡ።\n"
    "ስለ ቁርአን፣ ሐዲስ፣ ሶላት እና እስልምና ማንኛውንም ጥያቄ በቀጥታ ይላኩልኝ - በአማርኛ እመልሳለሁ።\n\n"
    "📌 /help - የትዕዛዞች ዝርዝር\n"
    f"📢 ቻናላችን፦ {CHANNEL_USERNAME}"
)

HELP_TEXT = (
    "*የሚገኙ ትዕዛዞች፦*\n"
    "/start - ቦቱን ማስጀመር\n"
    "/help - ይህ የእገዛ መልእክት\n"
    "/ask <ጥያቄ> - ስለ እስልምና ጥያቄ መጠየቅ (ለምሳሌ: /ask ሶላት ስንት ናቸው)\n\n"
    "ያለ ትዕዛዝ በቀጥታ መልእክት ቢልኩም እመልስልዎታለሁ።"
)

# ------------------------------------------------------------------
# DAILY HADITH/AYAH POOL (add as many as you like)
# ------------------------------------------------------------------
DAILY_CONTENT = [
    "📖 «በእርግጥ ከጸሎት በኋላ በጣም የሚወደው ስራ በሰዓቱ የሚደረግ ስራ ነው» (ሐዲስ - ቡኻሪ)",
    "📖 «አላህ ገር ነው፤ ገርነትንም ይወዳል» (ሐዲስ - ሙስሊም)",
    "📖 «ከናንተ በላጩ ቁርኣንን የተማረ እና ያስተማረ ነው» (ሐዲስ - ቡኻሪ)",
    "📖 «እነሆ ከችግር ጋር ምቾት አለ» (ቁርአን 94:6)",
]

# ------------------------------------------------------------------
# HANDLERS
# ------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"🕌 {member.first_name}, እንኳን ደህና መጡ ወደ IBN ABBAS QURAN CENTER!"
        )


def ask_claude(question: str) -> str:
    """Send a question to Claude and return the Amharic answer."""
    system_prompt = (
        "You are an Islamic knowledge assistant for 'Ibn Abbas Quran Center, Hara Town'. "
        "Answer questions about Quran, Hadith, Salah, Islamic history and general Islamic "
        "knowledge, following mainstream Sunni scholarship. "
        "ALWAYS answer in Amharic (አማርኛ) unless the user explicitly writes in English or Arabic. "
        "Keep answers concise, respectful, and cite Quran/Hadith when relevant. "
        "If unsure or the topic requires a qualified scholar's fatwa, say so honestly "
        "and recommend consulting a local scholar."
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            system=system_prompt,
            messages=[{"role": "user", "content": question}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "ይቅርታ፣ አሁን ጥያቄዎን መመለስ አልቻልኩም። እባክዎ ትንሽ ቆይተው ይሞክሩ።"


async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("እባክዎ ከ /ask በኋላ ጥያቄዎን ይጻፉ። ለምሳሌ፦ /ask ሶላት ስንት ናቸው")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    answer = ask_claude(question)
    await update.message.reply_text(answer)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    text_lower = text.lower()

    # 1. Check keyword auto-replies first
    for keyword, reply in AUTO_REPLIES.items():
        if keyword in text:
            await update.message.reply_text(reply)
            return

    # 2. Otherwise fall back to AI Q&A
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    answer = ask_claude(text)
    await update.message.reply_text(answer)


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: /broadcast <message> sends to the channel."""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("ይህ ትዕዛዝ ለአስተዳዳሪ ብቻ ነው።")
        return
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("እባክዎ ከ /broadcast በኋላ መልእክቱን ይጻፉ።")
        return
    await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=message)
    await update.message.reply_text("✅ ተልኳል!")


async def daily_post(context: ContextTypes.DEFAULT_TYPE):
    """Runs once a day - posts a Hadith/Ayah to the channel."""
    content = random.choice(DAILY_CONTENT)
    try:
        await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=content)
        logger.info("Daily post sent.")
    except Exception as e:
        logger.error(f"Failed to send daily post: {e}")


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Schedule the daily post (requires: pip install "python-telegram-bot[job-queue]")
    if app.job_queue:
        app.job_queue.run_daily(daily_post, time=dtime(hour=POST_HOUR_UTC, minute=0))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
