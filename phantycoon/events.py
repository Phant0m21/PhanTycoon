import os
import sys
import asyncio
import random
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import BOT_START_TIME, CURRENCY, DEV_ID, EMBED_COLOR, TOKEN, WORK_MAX, WORK_MIN
from phantycoon.data import ORES, PICKAXES, UPGRADES
from phantycoon.database import *
from phantycoon.shop_data import load_shop, save_shop
from phantycoon.state import active_buffs, collect_cooldowns

# ==================== СОБЫТИЯ ====================

@bot.event
async def on_ready():
    print(f"Бот {bot.user} готов!")
    print(f"Валюта: {CURRENCY}")
    print(f"Запущен: {BOT_START_TIME.strftime('%d.%m.%Y %H:%M:%S')}")
