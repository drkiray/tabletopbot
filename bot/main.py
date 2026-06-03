import logging
from telegram.ext import Application
from bot.config import BOT_TOKEN
from bot.database import init_db
from bot.scheduler import build_scheduler
from bot.handlers.voting import get_voting_handlers
from bot.handlers.attendance import get_attendance_handlers
from bot.handlers.ratings import get_rating_handler
from bot.handlers.admin import get_admin_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    for handler in get_admin_handlers():
        app.add_handler(handler)

    app.add_handler(get_rating_handler())

    for handler in get_voting_handlers():
        app.add_handler(handler)

    for handler in get_attendance_handlers():
        app.add_handler(handler)

    scheduler = build_scheduler(app)
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()
