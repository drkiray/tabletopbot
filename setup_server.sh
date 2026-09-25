#!/bin/bash
set -e

SERVER="root@78.17.114.172"
REMOTE_DIR="/opt/tabletop_bot"

echo "=== Настройка сервера ==="

echo "Создаю директорию и устанавливаю Python..."
ssh "$SERVER" "
  apt-get install -y python3 python3-venv python3-pip > /dev/null 2>&1
  mkdir -p $REMOTE_DIR
  cd $REMOTE_DIR
  python3 -m venv .venv
  echo OK
"

echo "Копирую файлы бота..."
rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='*.db' \
  bot/ "$SERVER:$REMOTE_DIR/bot/"
scp requirements.txt "$SERVER:$REMOTE_DIR/"

echo "Устанавливаю зависимости..."
ssh "$SERVER" "cd $REMOTE_DIR && .venv/bin/pip install -r requirements.txt -q"

echo ""
echo "=== Теперь нужно задать переменные окружения ==="
echo "Введи данные бота (они сохранятся на сервере):"
echo ""

read -p "BOT_TOKEN: " BOT_TOKEN
read -p "ADMIN_ID (твой Telegram ID): " ADMIN_ID
read -p "GROUP_CHAT_ID: " GROUP_CHAT_ID

ssh "$SERVER" "cat > $REMOTE_DIR/.env << EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID
GROUP_CHAT_ID=$GROUP_CHAT_ID
DB_PATH=$REMOTE_DIR/tabletop.db
TZ=Europe/Moscow
EOF"

echo ""
echo "Запускаю бота..."
ssh "$SERVER" "
  cd $REMOTE_DIR
  set -a && source .env && set +a
  nohup .venv/bin/python -m bot.main > /var/log/tabletop_bot.log 2>&1 &
  echo Бот запущен, PID: \$!
"

echo ""
echo "=== Готово! Бот установлен и запущен ==="
echo "Лог: ssh $SERVER 'tail -f /var/log/tabletop_bot.log'"
