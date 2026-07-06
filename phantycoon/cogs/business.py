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
from phantycoon.interactions import safe_defer, safe_edit, safe_send

# ==================== COLLECT ====================

@bot.slash_command(name="collect", description="Collect business income (every 6 hours)")
async def collect(ctx: disnake.ApplicationCommandInteraction):
    await safe_defer(ctx)
    can, next_time = can_collect(ctx.author.id)
    if not can:
        embed = disnake.Embed(
            title="Collect is on cooldown",
            description=f"Next collect is available <t:{int(next_time.timestamp())}:R>",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    user_businesses = get_user_businesses(ctx.author.id)
    shop = load_shop()
    
    # Get business upgrade level
    user_data = get_user_data(ctx.author.id)
    business_level = user_data.get("business_optimization_level", 0)
    income_bonus = 0
    if business_level > 0:
        levels = UPGRADES["business_optimization"]["levels"]
        for i in range(business_level):
            income_bonus += levels[i]["income_bonus"]
    
    total_income = 0
    collected_businesses = []
    
    for business_name in user_businesses:
        if business_name in shop["business"]:
            base_income = shop["business"][business_name]["income"]
            bonus_amount = int(base_income * income_bonus / 100)
            total_income += base_income + bonus_amount
            collected_businesses.append(f"{shop['business'][business_name]['emoji']} {business_name} +{base_income + bonus_amount} {CURRENCY} (+{bonus_amount} bonus)")
    
    if total_income == 0:
        embed = disnake.Embed(
            title="Income Collected",
            description="You do not own any businesses yet. Buy one in /shop.",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await safe_send(ctx, embed=embed)
        return
    
    new_wallet = user_data["wallet"] + total_income
    update_user_wallet(ctx.author.id, new_wallet)
    update_last_collect(ctx.author.id)
    update_stats(ctx.author.id, total_earned=total_income, collect_earned=total_income)
    
    embed = disnake.Embed(
        title="Income Collected",
        description=f"You collected income from your businesses!\n\n" + "\n".join(collected_businesses),
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Total received",
        value=f"**{total_income}** {CURRENCY}",
        inline=False
    )
    embed.add_field(
        name="New balance",
        value=f"{new_wallet} {CURRENCY}",
        inline=False
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    await safe_send(ctx, embed=embed)
