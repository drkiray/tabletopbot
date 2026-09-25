from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from bot.database import get_open_poll, get_user_votes_for_poll
from bot.poll_manager import DAYS_ORDER


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = get_open_poll()
    if not poll:
        await update.message.reply_text("Сейчас нет активного голосования.")
        return

    user_id = update.effective_user.id
    user_votes = get_user_votes_for_poll(poll["id"], user_id)

    lines = ["📅 *Твои голоса на эту неделю:*\n"]
    for day in DAYS_ORDER:
        if day not in user_votes:
            lines.append(f"❓ {day} — не голосовал")
        elif user_votes[day]:
            lines.append(f"✅ {day} — идёшь")
        else:
            lines.append(f"❌ {day} — не идёшь")

    lines.append("\nНажми кнопку чтобы изменить:")

    keyboard = []
    for day in DAYS_ORDER:
        current = user_votes.get(day)
        yes_label = f"{'→ ' if current is True else ''}✅ {day}"
        no_label = f"{'→ ' if current is False else ''}❌ {day}"
        keyboard.append([
            InlineKeyboardButton(yes_label, callback_data=f"vote:{poll['id']}:{day}:yes"),
            InlineKeyboardButton(no_label,  callback_data=f"vote:{poll['id']}:{day}:no"),
        ])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def get_info_handler():
    return CommandHandler("info", info)
