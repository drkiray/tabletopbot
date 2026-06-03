from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import (
    upsert_user, create_poll, get_open_poll,
    record_vote, get_votes_for_poll
)
from bot.poll_manager import DAYS_ORDER

async def send_weekly_poll(context: ContextTypes.DEFAULT_TYPE):
    """Called by scheduler every Monday at 10:00."""
    from bot.config import GROUP_CHAT_ID
    existing = get_open_poll()
    if existing:
        return  # poll already open this week

    from datetime import date
    week_start = date.today().isoformat()
    poll_id = create_poll(week_start)

    keyboard = []
    for day in DAYS_ORDER:
        keyboard.append([
            InlineKeyboardButton(f"✅ {day}", callback_data=f"vote:{poll_id}:{day}:yes"),
            InlineKeyboardButton(f"❌ {day}", callback_data=f"vote:{poll_id}:{day}:no"),
        ])

    text = (
        "📅 *Голосование за день встречи!*\n\n"
        "Отметь каждый день — сможешь прийти или нет.\n"
        "Голосование закрывается в пятницу в 23:59."
    )
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    _, poll_id, day, answer = query.data.split(":")
    poll_id = int(poll_id)
    user = query.from_user
    can_attend = (answer == "yes")

    poll = get_open_poll()
    if not poll or poll["id"] != poll_id:
        await query.answer("Голосование уже закрыто.", show_alert=True)
        return

    upsert_user(user.id, user.username, user.first_name)
    record_vote(poll_id, user.id, day, can_attend)
    await query.answer(f"{'✅' if can_attend else '❌'} {day} — записано!")

def get_voting_handlers():
    return [
        CallbackQueryHandler(handle_vote_callback, pattern=r"^vote:\d+:.+:(yes|no)$"),
    ]
