# Tabletop Bot

## Деплой на Railway

1. Зарегистрируйся на railway.app
2. Создай новый проект → Deploy from GitHub repo
3. Добавь переменные окружения в Railway dashboard:
   - `BOT_TOKEN` — токен от @BotFather
   - `ADMIN_ID` — твой Telegram user ID (узнать через @userinfobot)
   - `GROUP_CHAT_ID` — ID группового чата (добавь бота в группу, напиши что-то, получи через @getidsbot)
   - `TZ` — Europe/Moscow (или твой часовой пояс)
4. Railway автоматически задеплоит бота

## Команды бота

**Для всех (в личке):**
- `/rate` — оценить игры

**Только для администратора:**
- `/add_game` — добавить игру
- `/games` — список всех игр с ID
- `/delete_game <id>` — удалить игру
- `/cancel_week` — отменить голосование текущей недели

## Импорт игр из CSV

```bash
python -m scripts.import_csv data/your_games.csv
```

CSV формат: `name,min_players,max_players,complexity`
