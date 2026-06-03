import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
GROUP_CHAT_ID = int(os.environ["GROUP_CHAT_ID"])
DB_PATH = os.environ.get("DB_PATH", "tabletop.db")
TZ = os.environ.get("TZ", "Europe/Moscow")
