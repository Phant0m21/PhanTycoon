import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# ==================== SETTINGS ====================
BASE_DIR = Path(__file__).resolve().parent.parent

# Token loading
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN was not found in .env!")

# CURRENCY
CURRENCY = "$"
WORK_MIN = 90
WORK_MAX = 150

# Developer ID
DEV_ID = 1548658707024576564

# Embed color (white)
EMBED_COLOR = 0xFFFFFF

EMBLEM_COLORS = {
    "White": {"hex": 0xFFFFFF, "prestige": 0, "reason": "Default color"},
    "Golden": {"hex": 0xFFE187, "prestige": 1, "reason": "Prestige 1"},
    "Blue": {"hex": 0x647EF4, "prestige": 2, "reason": "Prestige 2"},
    "Green": {"hex": 0x31CD12, "prestige": 5, "reason": "Prestige 5"},
    "Orange": {"hex": 0xFFAC1E, "prestige": 10, "reason": "Prestige 10"},
}

# Files
DB_FILE = BASE_DIR / "economy.db"
SHOP_FILE = BASE_DIR / "shop.json"

# Bot start time
BOT_START_TIME = datetime.now(timezone.utc)
