import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from bot.config import BOT_TOKEN, ADMIN_ID
from bot.database import init_db
from bot.scheduler import build_scheduler
from bot.handlers.voting import get_voting_handlers
from bot.handlers.attendance import get_attendance_handlers
from bot.handlers.ratings import get_rating_handler
from bot.handlers.admin import get_admin_handlers
from bot.handlers.info import get_info_handler
from bot.handlers.session_rating import get_session_rating_handler

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Deep link: /start rate_{poll_id} — launch session rating flow
    if context.args and context.args[0].startswith("rate_"):
        try:
            poll_id = int(context.args[0].split("_")[1])
        except (IndexError, ValueError):
            poll_id = None
        if poll_id is not None:
            from bot.database import upsert_user, get_session_games
            from bot.handlers.session_rating import send_session_game_rating
            user = update.effective_user
            upsert_user(user.id, user.username, user.first_name)
            games = get_session_games(poll_id)
            if games:
                await send_session_game_rating(context.bot, user.id, poll_id, 0)
            else:
                await update.message.reply_text("Игры этого вечера ещё не добавлены.")
            return

    text = (
        "Привет! Я бот для настольных игр 🎲\n"
        "Каждую неделю провожу голосование за день встречи в группе.\n\n"
        "*Команды для всех:*\n"
        "/info — посмотреть свои голоса на эту неделю и изменить их\n"
        "/rate — оценить игры (только в личке)\n"
    )
    if update.effective_user.id == ADMIN_ID:
        text += (
            "\n*Команды администратора:*\n"
            "/add\\_game — добавить игру\n"
            "/games — список всех игр с ID\n"
            "/delete\\_game <id> — удалить игру\n"
            "/cancel\\_week — отменить голосование текущей недели\n"
            "/restart\\_poll — перезапустить голосование (сброс голосов)\n"
            "/ratings — рейтинг всех игр по среднему баллу\n"
            "/stats — активность всех участников\n"
            "/stats @username — статистика конкретного участника\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    for handler in get_admin_handlers():
        app.add_handler(handler)

    app.add_handler(get_rating_handler())
    app.add_handler(get_info_handler())

    for handler in get_session_rating_handler():
        app.add_handler(handler)

    for handler in get_voting_handlers():
        app.add_handler(handler)

    for handler in get_attendance_handlers():
        app.add_handler(handler)

    scheduler = build_scheduler(app)
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()
