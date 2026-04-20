# Telegram API Credentials (Get from https://my.telegram.org)
API_ID = 28891870
API_HASH = "ffc3794690bf254d2867ac58fd293a60"
BOT_TOKEN = "8121712200:AAGCTolWz8zyum3T-e013LMrj_6rncQAsRc"
OWNER_ID = 7660990923

import os

# Load from .env if present
from dotenv import load_dotenv
load_dotenv()

# MongoDB Connection String
# DO NOT hardcode credentials. Using environment variables for security.
DATABASE_URI = os.getenv("DATABASE_URI", "mongodb+srv://musicbhaikon9910:krishna@cluster0.cwvegmt.mongodb.net")
DATABASE_NAME = os.getenv("DATABASE_NAME", "groupadbot")
