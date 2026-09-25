import functools
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
from bot.config import ADMIN_ID, GROUP_CHAT_ID
from bot.database import (
    add_game, delete_game, get_all_games, get_open_poll, cancel_poll, create_poll,
    get_game_by_name_icase, add_session_game, get_session_games,
    get_ratings_summary, get_game_ratings_detail, set_poll_message_ids,
    get_user_by_username, get_user_stats, get_all_users_stats, get_user_top_games,
)

def admin_only(func):
    @functools.wraps(func)
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
    try:
        context.user_data["game_min"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число:")
        return ADD_MIN
    await update.message.reply_text("Максимальное число игроков:")
    return ADD_MAX

async def add_game_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["game_max"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число:")
        return ADD_MAX
    await update.message.reply_text("Сложность (1-10):")
    return ADD_COMPLEXITY

async def add_game_complexity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        complexity = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число от 1 до 10:")
        return ADD_COMPLEXITY
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
    try:
        game_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID должен быть числом. Посмотри /games")
        return
    delete_game(game_id)
    await update.message.reply_text(f"Игра #{game_id} удалена.")

@admin_only
async def ratings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        game_name = " ".join(context.args)
        game, ratings = get_game_ratings_detail(game_name)
        if not game:
            await update.message.reply_text(f"Игра «{game_name}» не найдена.")
            return
        if not ratings:
            await update.message.reply_text(f"Оценок для «{game['name']}» пока нет.")
            return
        lines = [f"*{game['name']}*\n"]
        for r in ratings:
            name = r["first_name"] or r["username"] or "?"
            like = r["like_score"]
            comp = r["complexity_score"]
            comp_str = f"  💀{comp}" if comp is not None else ""
            lines.append(f"• {name}: ❤️{like}{comp_str}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    else:
        games = get_ratings_summary()
        if not games:
            await update.message.reply_text("Оценок пока нет.")
            return
        lines = ["*Рейтинг игр (по среднему баллу):*\n"]
        for i, g in enumerate(games, 1):
            avg = g["avg_score"] if g["avg_score"] is not None else "—"
            lines.append(f"{i}. {g['name']} — {avg}/10 ({g['num_ratings']} оц.)")
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "\n..."
        await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def cancel_week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = get_open_poll()
    if not poll:
        await update.message.reply_text("Нет активного голосования.")
        return
    cancel_poll(poll["id"])
    await update.message.reply_text("Голосование отменено.")
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text="😔 Встреча на этой неделе отменяется."
    )

@admin_only
async def restart_poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.handlers.voting import send_poll_to_chat
    from datetime import date

    poll = get_open_poll()
    if poll:
        # Edit tracker first (always works — bot owns the message, no delete perms needed)
        tracker_id = poll.get("tracker_message_id")
        if tracker_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=GROUP_CHAT_ID,
                    message_id=tracker_id,
                    text="♻️ Голосование перезапущено — смотри новое сообщение ниже."
                )
            except Exception:
                pass
        # Try to delete the buttons message
        poll_mid = poll.get("poll_message_id")
        if poll_mid:
            try:
                await context.bot.delete_message(GROUP_CHAT_ID, poll_mid)
            except Exception:
                pass
        cancel_poll(poll["id"])

    week_start = date.today().isoformat()
    poll_id = create_poll(week_start)
    poll_msg_id, tracker_msg_id = await send_poll_to_chat(context.bot, GROUP_CHAT_ID, poll_id)
    set_poll_message_ids(poll_id, poll_msg_id, tracker_msg_id)

    await update.message.reply_text("✅ Голосование перезапущено!")

@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        users = get_all_users_stats()
        if not users:
            await update.message.reply_text("Нет данных.")
            return
        lines = ["📊 <b>Активность участников:</b>\n"]
        for i, u in enumerate(users, 1):
            name = f"@{u['username']}" if u["username"] else (u["first_name"] or "?")
            lines.append(f"{i}. {name} — посетил: {u['confirmed']}, голосований: {u['polls_voted']}")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return

    user = get_user_by_username(context.args[0])
    if not user:
        uname = context.args[0].lstrip("@")
        await update.message.reply_text(f"Пользователь @{uname} не найден в базе.")
        return

    s = get_user_stats(user["id"])
    top_games = get_user_top_games(user["id"])
    name = f"@{user['username']}" if user["username"] else (user["first_name"] or "?")
    fav = s["fav_day"] or "—"

    lines = [
        f"📊 <b>Статистика: {name}</b>\n",
        f"🗳 Голосований: <b>{s['polls_voted']}</b>",
        f"✅ Положительных голосов за дни: <b>{s['positive_votes']}</b> из {s['total_days_voted']}",
        f"🎯 Посетил: <b>{s['confirmed']}</b>",
        f"❌ Отказался: <b>{s['declined']}</b>",
        f"⭐ Игр оценено: <b>{s['games_rated']}</b>",
        f"📅 Любимый день: <b>{fav}</b>",
    ]
    if top_games:
        lines.append("\n🏆 <b>Топ-5 любимых игр:</b>")
        for i, g in enumerate(top_games, 1):
            lines.append(f"{i}. {g['name']} — {g['like_score']}/10")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

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

async def handle_admin_session_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles admin's reply with played game names after the session."""
    if update.effective_user.id != ADMIN_ID:
        return
    if update.effective_chat.type != "private":
        return

    session = context.bot_data.get("awaiting_session")
    if not session:
        return

    poll_id = session["poll_id"]
    text = update.message.text.strip()
    raw_names = [n.strip() for n in text.replace("\n", ",").split(",") if n.strip()]

    added, created = [], []
    for name in raw_names:
        game = get_game_by_name_icase(name)
        if not game:
            add_game(name, min_players=2, max_players=6, complexity=5)
            game = get_game_by_name_icase(name)
            created.append(game["name"])
        else:
            added.append(game["name"])
        add_session_game(poll_id, game["id"])

    context.bot_data.pop("awaiting_session", None)

    lines = ["✅ Записал игры вечера:\n"]
    for name in added:
        lines.append(f"• {name}")
    for name in created:
        lines.append(f"• {name} _(новая, добавлена в базу)_")
    lines.append("\nОтправляю запросы оценок участникам...")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    # Send rating requests to confirmed attendees
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from bot.database import get_confirmed_attendees
    from bot.handlers.session_rating import send_session_game_rating

    attendee_ids = get_confirmed_attendees(poll_id)
    games = get_session_games(poll_id)
    if not games:
        return

    sent, failed = 0, 0
    for user_id in attendee_ids:
        try:
            await send_session_game_rating(context.bot, user_id, poll_id, 0)
            sent += 1
        except Exception:
            failed += 1

    # Post deep-link button in group for anyone who hasn't interacted with the bot
    from bot.database import get_attendance_with_users
    attendance_rows = get_attendance_with_users(poll_id)
    attendee_names = [
        f"@{r['username']}" if r["username"] else (r["first_name"] or "?")
        for r in attendance_rows if r["confirmed"]
    ]
    names_str = ", ".join(attendee_names) if attendee_names else "участники"

    bot_username = (await context.bot.get_me()).username
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=f"🎲 Как прошёл вечер? Оцени сыгранные игры!\n\n👥 Были на встрече: {names_str}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Оценить игры →",
                url=f"https://t.me/{bot_username}?start=rate_{poll_id}"
            )
        ]])
    )
    if failed:
        await update.message.reply_text(
            f"⚠️ {sent} запросов отправлено в личку, {failed} не получилось (не писали боту) — они увидят кнопку в канале."
        )


def get_admin_session_handler():
    return MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_admin_session_input
    )


def get_admin_handlers():
    return [
        get_add_game_handler(),
        CommandHandler("games", list_games_command),
        CommandHandler("delete_game", delete_game_command),
        CommandHandler("cancel_week", cancel_week_command),
        CommandHandler("restart_poll", restart_poll_command),
        CommandHandler("ratings", ratings_command),
        CommandHandler("stats", stats_command),
        get_admin_session_handler(),
    ]
