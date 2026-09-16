import os
import sys
import asyncio
import random
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import BOT_START_TIME, CURRENCY, DEV_ID, EMBED_COLOR, TOKEN, WORK_MAX, WORK_MIN
from phantycoon.data import LAPIS_EMOJI, ORES, PICKAXES, UPGRADES
from phantycoon.database import *
from phantycoon.shop_data import load_shop, save_shop
from phantycoon.interactions import safe_defer, safe_embed, safe_send
from phantycoon.progression import add_prestige_ready_notice, add_quest_rewards_to_embed, expired_boost_notice, record_quest_event

# ==================== COMMANDS ====================


@bot.slash_command(name="work", description="Earn cash")
async def work(ctx: disnake.ApplicationCommandInteraction):
    notice = expired_boost_notice(ctx.author.id)
    if notice:
        await safe_embed(ctx, "Boost ended", notice, ephemeral=True)
    can, next_time = can_work(ctx.author.id)
    if not can:
        embed = disnake.Embed(
            title="Work is on cooldown",
            description=f"You already worked. Next shift is available <t:{int(next_time.timestamp())}:R>",
            color=get_user_emblem_color(ctx.author.id)
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await safe_send(ctx, embed=embed, ephemeral=True)
        return

    await safe_defer(ctx)
    earnings = random.randint(WORK_MIN, WORK_MAX)
    
    user_data = get_user_data(ctx.author.id)
    prestige_income_multiplier = get_prestige_income_multiplier(user_data)
    if prestige_income_multiplier > 1:
        earnings = int(earnings * prestige_income_multiplier)

    new_wallet = user_data["wallet"] + earnings
    update_user_wallet(ctx.author.id, new_wallet)
    update_last_work(ctx.author.id)
    update_stats(ctx.author.id, total_earned=earnings, work_earned=earnings, work_count=1, prestige_work_count=1)
    clan_progress = grant_clan_xp(ctx.author.id, CLAN_WORK_XP)

    embed = disnake.Embed(
        title="Work",
        description=f"You earned **{earnings}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    quest_rewards = record_quest_event(ctx.author.id, "work_actions", 1)
    quest_rewards += record_quest_event(ctx.author.id, "work_income", earnings)
    if clan_progress:
        quest_rewards += record_quest_event(ctx.author.id, "clan_xp", CLAN_WORK_XP)
    add_quest_rewards_to_embed(embed, quest_rewards)
    add_prestige_ready_notice(embed, ctx.author.id)
    
    await safe_send(ctx, embed=embed)


