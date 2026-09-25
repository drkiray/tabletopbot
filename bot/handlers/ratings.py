from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from bot.database import (
    upsert_user, get_all_games, add_or_update_rating_full, get_user_rating
)

CHOOSE_GAME, RATE_LIKE, RATE_COMPLEXITY = range(3)

async def rate_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Оценки ставятся в личке — напиши мне в личку!")
        return ConversationHandler.END

    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)
    games = get_all_games()

    if not games:
        await update.message.reply_text("База игр пока пуста.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(g["name"], callback_data=f"rategame:{g['id']}")]
        for g in games
    ]
    await update.message.reply_text(
        "Выбери игру для оценки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_GAME

async def choose_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_id = int(query.data.split(":")[1])
    context.user_data["rating_game_id"] = game_id

    existing = get_user_rating(query.from_user.id, game_id)
    existing_text = f" (текущая оценка: {existing['like_score']}/10)" if existing else ""

    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"likescore:{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"likescore:{i}") for i in range(6, 11)],
    ]
    await query.edit_message_text(
        f"Насколько тебе нравится эта игра?{existing_text}\n\nПоставь оценку от 1 до 10:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return RATE_LIKE

async def receive_like_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    score = int(query.data.split(":")[1])
    context.user_data["rating_like_score"] = score

    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"complexity:{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"complexity:{i}") for i in range(6, 11)],
    ]
    await query.edit_message_text(
        f"❤️ {score}/10 — записано!\n\nТеперь оцени сложность игры (1 = очень простая, 10 = очень сложная):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return RATE_COMPLEXITY

async def receive_complexity_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    complexity = int(query.data.split(":")[1])
    like_score = context.user_data.get("rating_like_score")
    game_id = context.user_data.get("rating_game_id")
    user = query.from_user

    add_or_update_rating_full(user.id, game_id, like_score, complexity)
    await query.edit_message_text(
        f"✅ Оценка сохранена: ❤️{like_score}/10, 💀{complexity}/10\n\nНапиши /rate чтобы оценить другую игру."
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

def get_rating_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("rate", rate_start)],
        states={
            CHOOSE_GAME: [CallbackQueryHandler(choose_game, pattern=r"^rategame:\d+$")],
            RATE_LIKE: [CallbackQueryHandler(receive_like_score, pattern=r"^likescore:\d+$")],
            RATE_COMPLEXITY: [CallbackQueryHandler(receive_complexity_score, pattern=r"^complexity:\d+$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

async def request_post_session_ratings(context: ContextTypes.DEFAULT_TYPE):
    """Called by scheduler at 23:00 on meeting day. Asks admin which games were played."""
    from bot.config import ADMIN_ID
    from bot.database import _conn
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

    context.bot_data["awaiting_session"] = {"poll_id": poll["id"]}

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "🎲 Как прошёл вечер?\n\n"
            "Напиши какие игры сыграли сегодня — каждую с новой строки или через запятую.\n"
            "Если игры нет в базе — добавлю автоматически."
        )
    )
