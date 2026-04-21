# Telegram API Credentials (Get from https://my.telegram.org)
API_ID = 28891870
API_HASH = "ffc3794690bf254d2867ac58fd293a60"
BOT_TOKEN = "your_bot_token_here"
OWNER_ID = 7660990923

# Multiple API IDs and Hashes for userbots to distribute load
USERBOT_APIS = [
    {"API_ID": 28721605, "API_HASH": "47391ca6ebea79e53804528ea558b62a"},
    {"API_ID": 27942193, "API_HASH": "2a59c314bd433ee8147347dd11d32f6b"},
    {"API_ID": 29369295, "API_HASH": "d363ad400d4ec80b8ad762e85c7bb1d4"},
    {"API_ID": 26564278, "API_HASH": "bf5589198faa75f11a25e87454eebb81"},
    {"API_ID": 20147962, "API_HASH": "7bbc3bc08a149bbd97ef7ca2c2247b0a"}
]

import random
def get_random_api():
    return random.choice(USERBOT_APIS)

import os

# Load from .env if present
from dotenv import load_dotenv
load_dotenv()

# MongoDB Connection String
# DO NOT hardcode credentials. Using environment variables for security.
DATABASE_URI = os.getenv("DATABASE_URI", "mongodb+srv://musicbhaikon9910:krishna@cluster0.cwvegmt.mongodb.net")
DATABASE_NAME = os.getenv("DATABASE_NAME", "groupadbot")
