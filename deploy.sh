#!/bin/bash
set -e

SERVER="tabletop"
REMOTE_DIR="/opt/tabletop_bot"

echo "Копирую файлы на сервер..."
rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='*.db' \
  bot/ "$SERVER:$REMOTE_DIR/bot/"
rsync -av --exclude='__pycache__' --exclude='*.pyc' \
  scripts/ "$SERVER:$REMOTE_DIR/scripts/"

echo "Перезапускаю бота..."
ssh "$SERVER" "systemctl restart tabletop-bot"

echo "Готово! Бот обновлён и запущен."
