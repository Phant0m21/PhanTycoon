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
DEV_ID = 1520822914516123791

# Embed color (white)
EMBED_COLOR = 0xFFFFFF

# Files
DB_FILE = BASE_DIR / "economy.db"
SHOP_FILE = BASE_DIR / "shop.json"

# Bot start time
BOT_START_TIME = datetime.now(timezone.utc)
