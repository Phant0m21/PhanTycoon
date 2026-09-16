import os
import sys
import asyncio
import random
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import BOT_START_TIME, CURRENCY, DEV_ID, EMBED_COLOR, TOKEN, WORK_MAX, WORK_MIN
from phantycoon.data import ORES, PICKAXES, PRESTIGE_TOKEN_EMOJI, UPGRADES
from phantycoon.database import *
from phantycoon.shop_data import load_shop, save_shop
from phantycoon.interactions import safe_defer, safe_embed, safe_send
from phantycoon.progression import add_prestige_ready_notice, add_quest_rewards_to_embed, expired_boost_notice, record_quest_event

# ==================== COLLECT ====================

@bot.slash_command(name="collect", description="Collect business income (every 6 hours)")
async def collect(ctx: disnake.ApplicationCommandInteraction):
    notice = expired_boost_notice(ctx.author.id)
    if notice:
        await safe_embed(ctx, "Boost ended", notice, ephemeral=True)
    can, next_time = can_collect(ctx.author.id)
    if not can:
        embed = disnake.Embed(
            title="Collect is on cooldown",
            description=f"Next collect is available <t:{int(next_time.timestamp())}:R>",
                color=get_user_emblem_color(ctx.author.id)
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
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    prestige_income_multiplier = get_prestige_income_multiplier(user_data)
    if prestige_income_multiplier > 1:
        prestige_bonus = int(total_income * (prestige_income_multiplier - 1))
        total_income += prestige_bonus
        collected_businesses.append(f"{PRESTIGE_TOKEN_EMOJI} Prestige bonus +{prestige_bonus} {CURRENCY}")


    await safe_defer(ctx)
    new_wallet = user_data["wallet"] + total_income
    update_user_wallet(ctx.author.id, new_wallet)
    update_last_collect(ctx.author.id)
    update_stats(ctx.author.id, total_earned=total_income, collect_earned=total_income)
    
    embed = disnake.Embed(
        title="Income Collected",
        description=f"Collected: **+{total_income:,}{CURRENCY}**\nBalance: **{new_wallet:,}{CURRENCY}**",
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    quest_rewards = record_quest_event(ctx.author.id, "collect_actions", 1)
    quest_rewards += record_quest_event(ctx.author.id, "collect_income", total_income)
    add_quest_rewards_to_embed(embed, quest_rewards)
    add_prestige_ready_notice(embed, ctx.author.id)
    
    await safe_send(ctx, embed=embed)
