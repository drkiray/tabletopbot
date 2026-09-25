import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import (
    upsert_user, create_poll, get_open_poll,
    record_vote, get_votes_for_poll, get_votes_with_users,
    set_poll_message_ids,
)
from bot.poll_manager import DAYS_ORDER

DAY_ACCUSATIVE = {
    "Вторник":     "Вторник",
    "Среда":       "Среду",
    "Четверг":     "Четверг",
    "Пятница":     "Пятницу",
    "Суббота":     "Субботу",
    "Воскресенье": "Воскресенье",
}

def _build_tracker_text(poll_id):
    votes = get_votes_with_users(poll_id)
    day_attendees = {day: [] for day in DAYS_ORDER}
    seen = {day: set() for day in DAYS_ORDER}
    for v in votes:
        if v["can_attend"] and v["day"] in day_attendees:
            name = f"@{v['username']}" if v["username"] else (v["first_name"] or "?")
            if name not in seen[v["day"]]:
                seen[v["day"]].add(name)
                day_attendees[v["day"]].append(name)
    lines = ["👥 <b>Кто может прийти:</b>\n"]
    for day in DAYS_ORDER:
        attendees = day_attendees[day]
        lines.append(f"<b>{day}:</b> {', '.join(attendees) if attendees else '—'}")
    return "\n".join(lines)

async def send_poll_to_chat(bot, chat_id, poll_id):
    """Send poll keyboard + tracker. Returns (poll_message_id, tracker_message_id)."""
    keyboard = []
    for day in DAYS_ORDER:
        keyboard.append([
            InlineKeyboardButton(f"✅ {day}", callback_data=f"vote:{poll_id}:{day}:yes"),
            InlineKeyboardButton(f"❌ {day}", callback_data=f"vote:{poll_id}:{day}:no"),
        ])
    poll_msg = await bot.send_message(
        chat_id=chat_id,
        text=(
            "📅 *Голосование за день встречи!*\n\n"
            "Отметь каждый день — сможешь прийти или нет.\n"
            "Голосование закрывается в пятницу в 10:00.\n\n"
            "❗️ Отрицательный ответ есть смысл нажимать только, если вы передумали и решили убрать себя с определённого дня. В противном случае это ни на что не влияет."
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    tracker_msg = await bot.send_message(
        chat_id=chat_id,
        text=_build_tracker_text(poll_id),
        parse_mode="HTML"
    )
    try:
        await bot.pin_chat_message(chat_id=chat_id, message_id=tracker_msg.message_id)
    except Exception:
        pass
    return poll_msg.message_id, tracker_msg.message_id

async def _update_tracker(bot, chat_id, poll):
    tracker_id = poll.get("tracker_message_id")
    if not tracker_id:
        return
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=tracker_id,
            text=_build_tracker_text(poll["id"]),
            parse_mode="HTML"
        )
    except Exception:
        pass

async def send_weekly_poll(context: ContextTypes.DEFAULT_TYPE):
    """Called by scheduler every Monday at 10:00."""
    from bot.config import GROUP_CHAT_ID
    existing = get_open_poll()
    if existing:
        return

    from datetime import date
    week_start = date.today().isoformat()
    poll_id = create_poll(week_start)
    poll_msg_id, tracker_msg_id = await send_poll_to_chat(context.bot, GROUP_CHAT_ID, poll_id)
    set_poll_message_ids(poll_id, poll_msg_id, tracker_msg_id)

async def handle_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.config import GROUP_CHAT_ID
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
    await _update_tracker(context.bot, GROUP_CHAT_ID, poll)

def get_voting_handlers():
    return [
        CallbackQueryHandler(handle_vote_callback, pattern=r"^vote:\d+:.+:(yes|no)$"),
    ]

async def close_weekly_poll(context: ContextTypes.DEFAULT_TYPE):
    """Called by scheduler every Friday at 23:59."""
    from bot.config import GROUP_CHAT_ID
    from bot.poll_manager import determine_winner
    from bot.database import close_poll, cancel_poll, get_votes_for_poll

    poll = get_open_poll()
    if not poll:
        return

    votes = get_votes_for_poll(poll["id"])
    winner = determine_winner(votes)

    if not winner:
        if cancel_poll(poll["id"]):
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text="😔 Никто не проголосовал — встреча на этой неделе отменяется."
            )
        return

    vote_counts = {}
    for v in votes:
        vote_counts[v["day"]] = vote_counts.get(v["day"], 0) + 1

    winner_count = vote_counts.get(winner, 0)
    if winner_count < 3:
        if cancel_poll(poll["id"]):
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text="😔 К сожалению, на этой неделе не набралось достаточного количества участников — встреча не состоится. Увидимся на следующей неделе!"
            )
        return

    if not close_poll(poll["id"], winner):
        return
    attendee_count = winner_count

    winner_votes = [v for v in get_votes_with_users(poll["id"]) if v["day"] == winner and v["can_attend"]]
    mentions = []
    for v in winner_votes:
        name = f"@{v['username']}" if v["username"] else (v["first_name"] or "?")
        mentions.append(f'<a href="tg://user?id={v["user_id"]}">{html.escape(name)}</a>')
    mentions_str = ", ".join(mentions) if mentions else "—"

    keyboard = [[
        InlineKeyboardButton("✅ Приду!", callback_data=f"attend:{poll['id']}:yes"),
        InlineKeyboardButton("❌ Не смогу", callback_data=f"attend:{poll['id']}:no"),
    ]]

    text = (
        f"🎲 <b>Встречаемся в {DAY_ACCUSATIVE.get(winner, winner)}!</b>\n\n"
        f"Смогут прийти: ~{attendee_count} чел.\n"
        f"{mentions_str}\n\n"
        "Подтверди своё участие:"
    )
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

    from bot.handlers.attendance import send_attendance_tracker
    from bot.database import set_attendance_tracker_message_id
    tracker_msg_id = await send_attendance_tracker(context.bot, GROUP_CHAT_ID, poll["id"])
    set_attendance_tracker_message_id(poll["id"], tracker_msg_id)

def _load_all_ratings():
    """Returns {user_id: {game_id: like_score}} for recommender."""
    from bot.database import _conn
    import sqlite3
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT user_id, game_id, like_score FROM ratings").fetchall()
    result = {}
    for r in rows:
        result.setdefault(r["user_id"], {})[r["game_id"]] = r["like_score"]
    return result
