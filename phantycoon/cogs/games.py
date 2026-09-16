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
from phantycoon.interactions import safe_defer, safe_send
from phantycoon.progression import add_prestige_ready_notice, add_quest_rewards_to_embed, record_quest_event

# ==================== COINFLIP ====================

@bot.slash_command(name="coinflip", description="Flip a coin (x2)")
async def coinflip(
    ctx: disnake.ApplicationCommandInteraction,
    bet: int = commands.Param(gt=0, description="Bet amount"),
    choice: str = commands.Param(choices=["Heads", "Tails"], description="Your pick")
):
    user_id = ctx.author.id
    
    user_data = get_user_data(user_id)
    if user_data["wallet"] < bet:
        embed = disnake.Embed(
            title="Error",
            description="Not enough cash!",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    await safe_defer(ctx)
    update_user_wallet(user_id, user_data["wallet"] - bet)
    
    result = random.choice(["Heads", "Tails"])
    
    if result == choice:
        win_amount = bet * 2
        user_data = get_user_data(user_id)
        update_user_wallet(user_id, user_data["wallet"] + win_amount)
        update_stats(user_id, total_earned=win_amount, games_played=1)
        
        embed = disnake.Embed(
            title="Coinflip",
            description=f"**Result: {result}**\n\n{ctx.author.mention} won **{win_amount}** {CURRENCY} (x2)",
            color=EMBED_COLOR
        )
    else:
        embed = disnake.Embed(
            title="Coinflip",
            description=f"**Result: {result}**\n\n{ctx.author.mention} lost **{bet}** {CURRENCY}",
            color=EMBED_COLOR
        )
        
        update_stats(user_id, total_spent=bet, games_played=1)
    
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    quest_rewards = record_quest_event(user_id, "games_played", 1)
    if result == choice:
        quest_rewards += record_quest_event(user_id, "games_won", 1)
        quest_rewards += record_quest_event(user_id, "game_winnings", win_amount)
    add_quest_rewards_to_embed(embed, quest_rewards)
    add_prestige_ready_notice(embed, user_id)
    await safe_send(ctx, embed=embed)
