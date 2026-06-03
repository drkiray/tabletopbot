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

async def close_weekly_poll(context: ContextTypes.DEFAULT_TYPE):
    """Called by scheduler every Friday at 23:59."""
    from bot.config import GROUP_CHAT_ID
    from bot.poll_manager import determine_winner
    from bot.database import close_poll, cancel_poll, get_all_games, get_votes_for_poll
    from bot.recommender import recommend_games

    poll = get_open_poll()
    if not poll:
        return

    votes = get_votes_for_poll(poll["id"])
    winner = determine_winner(votes)

    if not winner:
        cancel_poll(poll["id"])
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text="😔 Никто не проголосовал — встреча на этой неделе отменяется."
        )
        return

    close_poll(poll["id"], winner)

    vote_counts = {}
    for v in votes:
        vote_counts[v["day"]] = vote_counts.get(v["day"], 0) + 1

    games = get_all_games()
    ratings = _load_all_ratings()
    attendee_count = vote_counts.get(winner, 1)
    top_games = recommend_games(games, ratings, attendee_count=attendee_count)

    games_text = "\n".join(
        f"{i+1}. {g['name']} ({g['min_players']}–{g['max_players']} игроков, сложность {g['complexity']}/10)"
        for i, g in enumerate(top_games)
    ) or "Игры не найдены 😔"

    keyboard = [[
        InlineKeyboardButton("✅ Приду!", callback_data=f"attend:{poll['id']}:yes"),
        InlineKeyboardButton("❌ Не смогу", callback_data=f"attend:{poll['id']}:no"),
    ]]

    text = (
        f"🎲 *Встречаемся в {winner}!*\n\n"
        f"Смогут прийти: ~{attendee_count} чел.\n\n"
        f"*Предварительные рекомендации игр:*\n{games_text}\n\n"
        "Подтверди своё участие:"
    )
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

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
