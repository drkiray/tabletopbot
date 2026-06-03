from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
from bot.config import ADMIN_ID
from bot.database import add_game, delete_game, get_all_games, get_open_poll, cancel_poll

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("Нет доступа.")
            return
        return await func(update, context)
    return wrapper

ADD_NAME, ADD_MIN, ADD_MAX, ADD_COMPLEXITY = range(4)

@admin_only
async def add_game_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи название игры:")
    return ADD_NAME

async def add_game_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["game_name"] = update.message.text.strip()
    await update.message.reply_text("Минимальное число игроков:")
    return ADD_MIN

async def add_game_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["game_min"] = int(update.message.text.strip())
    await update.message.reply_text("Максимальное число игроков:")
    return ADD_MAX

async def add_game_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["game_max"] = int(update.message.text.strip())
    await update.message.reply_text("Сложность (1-10):")
    return ADD_COMPLEXITY

async def add_game_complexity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    complexity = int(update.message.text.strip())
    name = context.user_data["game_name"]
    add_game(
        name=name,
        min_players=context.user_data["game_min"],
        max_players=context.user_data["game_max"],
        complexity=complexity,
    )
    await update.message.reply_text(f"✅ Игра «{name}» добавлена!")
    return ConversationHandler.END

@admin_only
async def list_games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games = get_all_games()
    if not games:
        await update.message.reply_text("База игр пуста.")
        return
    text = "\n".join(
        f"{g['id']}. {g['name']} ({g['min_players']}–{g['max_players']} игр., слож. {g['complexity']}/10)"
        for g in games
    )
    await update.message.reply_text(f"Список игр:\n{text}")

@admin_only
async def delete_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /delete_game <id>\nПосмотри ID через /games")
        return
    game_id = int(args[0])
    delete_game(game_id)
    await update.message.reply_text(f"Игра #{game_id} удалена.")

@admin_only
async def cancel_week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = get_open_poll()
    if not poll:
        await update.message.reply_text("Нет активного голосования.")
        return
    cancel_poll(poll["id"])
    await update.message.reply_text("Голосование отменено, встреча на этой неделе не состоится.")

def get_add_game_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("add_game", add_game_start)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_game_name)],
            ADD_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_game_min)],
            ADD_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_game_max)],
            ADD_COMPLEXITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_game_complexity)],
        },
        fallbacks=[],
    )

def get_admin_handlers():
    return [
        get_add_game_handler(),
        CommandHandler("games", list_games_command),
        CommandHandler("delete_game", delete_game_command),
        CommandHandler("cancel_week", cancel_week_command),
    ]
