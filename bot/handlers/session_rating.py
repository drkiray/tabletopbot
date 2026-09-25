from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.database import upsert_user, add_or_update_rating_full, get_session_games


async def send_session_game_rating(bot, user_id, poll_id, game_index):
    games = get_session_games(poll_id)
    if game_index >= len(games):
        await bot.send_message(
            chat_id=user_id,
            text="✅ Спасибо за оценки! Увидимся на следующей встрече 🎲"
        )
        return

    game = games[game_index]
    total = len(games)
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"srate:{poll_id}:{game_index}:{i}") for i in range(0, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"srate:{poll_id}:{game_index}:{i}") for i in range(6, 11)],
    ]

    await bot.send_message(
        chat_id=user_id,
        text=f"🎲 *{game['name']}* ({game_index + 1}/{total})\nНасколько тебе понравилась игра? (0–10)",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def _ask_session_complexity(query, poll_id, game_index, like_score, game_name, total):
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"sratec:{poll_id}:{game_index}:{like_score}:{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"sratec:{poll_id}:{game_index}:{like_score}:{i}") for i in range(6, 11)],
    ]
    await query.edit_message_text(
        f"🎲 *{game_name}* ({game_index + 1}/{total})\n❤️ {like_score}/10 — записано!\n\nТеперь оцени сложность (1 = очень простая, 10 = очень сложная):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def handle_session_rate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, poll_id_str, index_str, score_str = query.data.split(":")
    poll_id = int(poll_id_str)
    game_index = int(index_str)
    like_score = int(score_str)

    games = get_session_games(poll_id)
    game = games[game_index]
    user = query.from_user
    upsert_user(user.id, user.username, user.first_name)

    await _ask_session_complexity(query, poll_id, game_index, like_score, game["name"], len(games))


async def handle_session_complexity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, poll_id_str, index_str, like_str, complexity_str = query.data.split(":")
    poll_id = int(poll_id_str)
    game_index = int(index_str)
    like_score = int(like_str)
    complexity = int(complexity_str)

    games = get_session_games(poll_id)
    game = games[game_index]
    user = query.from_user

    add_or_update_rating_full(user.id, game["id"], like_score, complexity)
    await query.edit_message_text(
        f"✅ *{game['name']}* — ❤️{like_score}/10, 💀{complexity}/10",
        parse_mode="Markdown"
    )

    await send_session_game_rating(context.bot, user.id, poll_id, game_index + 1)


def get_session_rating_handler():
    return [
        CallbackQueryHandler(handle_session_rate_callback, pattern=r"^srate:\d+:\d+:\d+$"),
        CallbackQueryHandler(handle_session_complexity_callback, pattern=r"^sratec:\d+:\d+:\d+:\d+$"),
    ]
