from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from bot.database import (
    upsert_user, get_all_games, add_or_update_rating, get_user_rating
)

CHOOSE_GAME, RATE_LIKE = range(2)

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
    game_id = context.user_data.get("rating_game_id")
    user = query.from_user

    add_or_update_rating(user.id, game_id, score)
    await query.edit_message_text(f"✅ Оценка {score}/10 сохранена! Напиши /rate чтобы оценить другую игру.")
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
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

async def request_post_session_ratings(context: ContextTypes.DEFAULT_TYPE):
    """Called by scheduler after the session (23:00 on meeting day)."""
    from bot.config import GROUP_CHAT_ID
    from bot.database import get_confirmed_attendees, _conn
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

    bot_username = (await context.bot.get_me()).username
    text = (
        f"🎲 Как прошёл вечер? Оцени игры в которые сыграли!\n"
        f"Напиши мне в личку: @{bot_username} → /rate"
    )
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=text)

    for user_id in attendee_ids:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Привет! Оцени игры сегодняшнего вечера — напиши /rate"
            )
        except Exception:
            pass
