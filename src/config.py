# Telegram API Credentials (Get from https://my.telegram.org)
API_ID = 28891870
API_HASH = "ffc3794690bf254d2867ac58fd293a60"
BOT_TOKEN = "your_bot_token_here"
OWNER_ID = 7660990923

import os

# MongoDB Connection String
DATABASE_URI = os.getenv("DATABASE_URI", "mongodb+srv://<USER>:<PASSWORD>@cluster0.cwvegmt.mongodb.net")
DATABASE_NAME = os.getenv("DATABASE_NAME", "file_sharing_bot")
