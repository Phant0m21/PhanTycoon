import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# ==================== НАСТРОЙКИ ====================
BASE_DIR = Path(__file__).resolve().parent.parent

# Загрузка токена
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Токен не найден в .env файле!")

# ВАЛЮТА
CURRENCY = "$"
WORK_MIN = 90
WORK_MAX = 150

# ID разработчика
DEV_ID = 1520143480406409256

# Цвет эмбеда (белый)
EMBED_COLOR = 0xFFFFFF

# Файлы
DB_FILE = BASE_DIR / "economy.db"
SHOP_FILE = BASE_DIR / "shop.json"

# Bot start time
BOT_START_TIME = datetime.now(timezone.utc)
