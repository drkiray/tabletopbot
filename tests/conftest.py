import os
import sys

os.environ.setdefault("BOT_TOKEN", "test_token")
os.environ.setdefault("ADMIN_ID", "1")
os.environ.setdefault("GROUP_CHAT_ID", "1")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
