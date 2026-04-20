# Telegram API Credentials (Get from https://my.telegram.org)
API_ID = 28891870
API_HASH = "ffc3794690bf254d2867ac58fd293a60"
BOT_TOKEN = "your_bot_token_here"
OWNER_ID = 7660990923

import os

# Load from .env if present
from dotenv import load_dotenv
load_dotenv()

# MongoDB Connection String - DO NOT HARDCODE SECRETS IN SOURCE CODE
DATABASE_URI = os.getenv("DATABASE_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "groupadbot")

if not DATABASE_URI:
    raise ValueError("DATABASE_URI environment variable must be set!")
