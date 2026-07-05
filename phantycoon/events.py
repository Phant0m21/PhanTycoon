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
from phantycoon.interactions import safe_defer, safe_send

# ==================== EVENTS ====================

@bot.event
async def on_ready():
    print(f"Bot {bot.user} ready!")
    print(f"Currency: {CURRENCY}")
    print(f"Started: {BOT_START_TIME.strftime('%d.%m.%Y %H:%M:%S')}")


@bot.listen("on_application_command")
async def auto_defer_application_commands(ctx: disnake.ApplicationCommandInteraction):
    await safe_defer(ctx)


@bot.event
async def on_slash_command_error(ctx: disnake.ApplicationCommandInteraction, error: Exception):
    print(f"Command error {getattr(ctx.application_command, 'qualified_name', 'unknown')}: {error!r}")
    embed = disnake.Embed(
        title="Error",
        description="The command could not finish right now. Try again in a few seconds.",
        color=EMBED_COLOR
    )
    await safe_send(ctx, embed=embed, ephemeral=True)
