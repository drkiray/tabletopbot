from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import (
    upsert_user, get_open_poll, record_attendance,
    get_confirmed_attendees, get_all_games, get_votes_for_poll,
    get_attendance_with_users, set_attendance_tracker_message_id,
)

def _build_attendance_tracker_text(poll_id):
    rows = get_attendance_with_users(poll_id)
    confirmed = []
    for r in rows:
        if r["confirmed"]:
            name = f"@{r['username']}" if r["username"] else (r["first_name"] or "?")
            confirmed.append(name)
    if confirmed:
        return "✅ <b>Придут:</b>\n\n" + "\n".join(confirmed)
    return "✅ <b>Придут:</b> пока никто"

async def send_attendance_tracker(bot, chat_id, poll_id):
    """Post attendance tracker message. Returns message_id."""
    msg = await bot.send_message(
        chat_id=chat_id,
        text=_build_attendance_tracker_text(poll_id),
        parse_mode="HTML"
    )
    return msg.message_id

async def _update_attendance_tracker(bot, chat_id, poll):
    tracker_id = poll.get("attendance_tracker_message_id")
    if not tracker_id:
        return
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=tracker_id,
            text=_build_attendance_tracker_text(poll["id"]),
            parse_mode="HTML"
        )
    except Exception:
        pass

async def handle_attendance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.config import GROUP_CHAT_ID
    from bot.database import _conn
    import sqlite3

    query = update.callback_query

    _, poll_id, answer = query.data.split(":")
    poll_id = int(poll_id)
    user = query.from_user
    confirmed = (answer == "yes")

    upsert_user(user.id, user.username, user.first_name)
    record_attendance(poll_id, user.id, confirmed)

    msg = "✅ Отлично, ждём тебя!" if confirmed else "❌ Жаль, в другой раз!"
    await query.answer(msg, show_alert=True)

    # Find the poll (may be closed) to get tracker message ID
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        poll = conn.execute("SELECT * FROM polls WHERE id = ?", (poll_id,)).fetchone()
    if poll:
        await _update_attendance_tracker(context.bot, GROUP_CHAT_ID, dict(poll))

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
            "SELECT * FROM polls ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not poll or poll["status"] != "closed":
        return

    poll = dict(poll)
    from datetime import date
    day_map = {"Вторник": 1, "Среда": 2, "Четверг": 3, "Пятница": 4, "Суббота": 5, "Воскресенье": 6}
    if date.today().weekday() != day_map.get(poll["chosen_day"], -1):
        return
    attendee_ids = get_confirmed_attendees(poll["id"])
    attendee_count = len(attendee_ids) if attendee_ids else 3

    games = get_all_games()
    all_ratings = _load_all_ratings()
    top_games = recommend_games(games, all_ratings, attendee_count=attendee_count, attendee_ids=attendee_ids or None)

    games_text = "\n".join(
        f"{i+1}. {g['name']} ({g['min_players']}–{g['max_players']} игр., сложность {g['complexity']}/10) — {reason}"
        for i, (g, reason) in enumerate(top_games)
    ) or "Игры не добавлены 😔"

    attendance_rows = get_attendance_with_users(poll["id"])
    attendee_names = [
        f"@{r['username']}" if r["username"] else (r["first_name"] or "?")
        for r in attendance_rows if r["confirmed"]
    ]
    names_str = ", ".join(attendee_names) if attendee_names else "—"
    confirmed_count = len(attendee_ids)

    text = (
        f"<b>🎲 Сегодня играем в настолки!</b>\n\n"
        f"Подтвердили участие: {confirmed_count} чел.\n"
        f"{names_str}\n\n"
        f"<b>Топ игр для вашей компании:</b>\n{games_text}\n\n"
        "Увидимся сегодня! 🃏"
    )
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=text,
        parse_mode="HTML"
    )

def get_attendance_handlers():
    return [
        CallbackQueryHandler(handle_attendance_callback, pattern=r"^attend:\d+:(yes|no)$"),
    ]
