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
from phantycoon.interactions import safe_send

# ==================== EVENTS ====================

HONEYPOT_CHANNEL_ID = 1535570511730311178
HONEYPOT_BAN_REASON = "Violation of protocol: interaction with an unroutable system node."


@bot.event
async def on_ready():
    print(f"Bot {bot.user} ready!")
    print(f"Currency: {CURRENCY}")
    print(f"Started: {BOT_START_TIME.strftime('%d.%m.%Y %H:%M:%S')}")


@bot.event
async def on_message(message: disnake.Message):
    if message.channel.id != HONEYPOT_CHANNEL_ID:
        return
    if not message.guild or message.author.id == bot.user.id:
        return

    author_is_admin = (
        isinstance(message.author, disnake.Member)
        and message.author.guild_permissions.administrator
    )
    if author_is_admin and not message.author.bot:
        return

    dm_embed = disnake.Embed(
        title="You have been banned from PhanTycoon Server",
        description=f"**Reason:** {HONEYPOT_BAN_REASON}",
        color=EMBED_COLOR,
    )
    try:
        await message.author.send(embed=dm_embed)
    except disnake.DiscordException:
        pass

    try:
        await message.guild.ban(
            message.author,
            reason=HONEYPOT_BAN_REASON,
            delete_message_days=0,
        )
    except disnake.DiscordException as error:
        print(f"Honeypot ban failed for {message.author.id}: {error!r}")


@bot.event
async def on_slash_command_error(ctx: disnake.ApplicationCommandInteraction, error: Exception):
    if isinstance(error, commands.CheckFailure):
        return

    print(f"Command error {getattr(ctx.application_command, 'qualified_name', 'unknown')}: {error!r}")
    embed = disnake.Embed(
        title="Error",
        description="The command could not finish right now. Try again in a few seconds.",
        color=EMBED_COLOR
    )
    await safe_send(ctx, embed=embed, ephemeral=True)
