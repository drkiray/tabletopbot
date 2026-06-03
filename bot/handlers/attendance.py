from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import (
    upsert_user, get_open_poll, record_attendance,
    get_confirmed_attendees, get_all_games, get_votes_for_poll
)

async def handle_attendance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    _, poll_id, answer = query.data.split(":")
    poll_id = int(poll_id)
    user = query.from_user
    confirmed = (answer == "yes")

    upsert_user(user.id, user.username, user.first_name)
    record_attendance(poll_id, user.id, confirmed)

    msg = "✅ Отлично, ждём тебя!" if confirmed else "❌ Жаль, в другой раз!"
    await query.answer(msg, show_alert=True)

async def send_day_of_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Called by scheduler on the morning of the chosen day at 10:00."""
    from bot.config import GROUP_CHAT_ID
    from bot.database import _conn
    from bot.recommender import recommend_games
    from bot.handlers.voting import _load_all_ratings
    import sqlite3

    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        poll = conn.execute(
            "SELECT * FROM polls WHERE status = 'closed' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not poll:
        return

    poll = dict(poll)
    attendee_ids = get_confirmed_attendees(poll["id"])
    attendee_count = len(attendee_ids) if attendee_ids else 3

    games = get_all_games()
    all_ratings = _load_all_ratings()
    attendee_ratings = {uid: all_ratings.get(uid, {}) for uid in attendee_ids}

    top_games = recommend_games(games, attendee_ratings, attendee_count=attendee_count)

    games_text = "\n".join(
        f"{i+1}. {g['name']} ({g['min_players']}–{g['max_players']} игроков, сложность {g['complexity']}/10)"
        for i, g in enumerate(top_games)
    ) or "Игры не добавлены 😔"

    confirmed_count = len(attendee_ids)
    text = (
        f"🎲 *Сегодня играем в настолки!*\n\n"
        f"Подтвердили участие: {confirmed_count} чел.\n\n"
        f"*Топ игр для вашей компании:*\n{games_text}\n\n"
        "Увидимся сегодня! 🃏"
    )
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=text,
        parse_mode="Markdown"
    )

def get_attendance_handlers():
    return [
        CallbackQueryHandler(handle_attendance_callback, pattern=r"^attend:\d+:(yes|no)$"),
    ]
