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

# ==================== КОМАНДЫ ====================

@bot.slash_command(name="balance", description="Показать баланс")
async def balance(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(default=None, description="Пользователь")
):
    target = user or ctx.author
    user_data = get_user_data(target.id)
    
    total = user_data["wallet"] + user_data["bank"]

    embed = disnake.Embed(
        title=f"Баланс пользователя - {target.name}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Всего",
        value=f"```\n{total}\n```",
        inline=False
    )
    embed.add_field(
        name="Кошелёк",
        value=f"```\n{user_data['wallet']}\n```",
        inline=True
    )
    embed.add_field(
        name="Банк",
        value=f"```\n{user_data['bank']}\n```",
        inline=True
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed)


@bot.slash_command(name="work", description="Заработать деньги")
async def work(ctx: disnake.ApplicationCommandInteraction):
    can, next_time = can_work(ctx.author.id)
    if not can:
        remaining = next_time - datetime.now(timezone.utc)
        wait_minutes = max(1, int(remaining.total_seconds() / 60))
        embed = disnake.Embed(
            title="Работа недоступна",
            description=f"Вы уже работали. Следующая работа доступна <t:{int(next_time.timestamp())}:R>",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await safe_send(ctx, embed=embed, ephemeral=True)
        return

    earnings = random.randint(WORK_MIN, WORK_MAX)
    
    # Проверка баффа от витаминов
    if ctx.author.id in active_buffs:
        boost_data = active_buffs[ctx.author.id]
        if boost_data["remaining"] > 0:
            boost_percent = 45
            bonus = int(earnings * boost_percent / 100)
            earnings += bonus
            boost_data["remaining"] -= 1
            if boost_data["remaining"] <= 0:
                del active_buffs[ctx.author.id]
    
    user_data = get_user_data(ctx.author.id)
    new_wallet = user_data["wallet"] + earnings
    update_user_wallet(ctx.author.id, new_wallet)
    update_last_work(ctx.author.id)
    update_stats(ctx.author.id, total_earned=earnings, work_earned=earnings, work_count=1)

    embed = disnake.Embed(
        title="Работа",
        description=f"Вы заработали **{earnings}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed)


@bot.slash_command(name="deposit", description="Положить деньги в банк")
async def deposit(
    ctx: disnake.ApplicationCommandInteraction,
    amount: str = commands.Param(description="Сумма или 'all'")
):
    user_data = get_user_data(ctx.author.id)
    
    if amount.lower() == "all":
        amount_to_deposit = user_data["wallet"]
    else:
        try:
            amount_to_deposit = int(amount)
        except ValueError:
            embed = disnake.Embed(
                title="Ошибка",
                description="Укажите число или 'all'",
                color=EMBED_COLOR
            )
            await safe_send(ctx, embed=embed, ephemeral=True)
            return
    
    if amount_to_deposit <= 0:
        embed = disnake.Embed(
            title="Ошибка",
            description="Сумма должна быть больше 0",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    if user_data["wallet"] < amount_to_deposit:
        embed = disnake.Embed(
            title="Ошибка",
            description=f"Недостаточно денег в кошельке!",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    new_wallet = user_data["wallet"] - amount_to_deposit
    new_bank = user_data["bank"] + amount_to_deposit
    
    update_user_wallet(ctx.author.id, new_wallet)
    update_user_bank(ctx.author.id, new_bank)
    
    embed = disnake.Embed(
        title="Депозит",
        description=f"Вы положили в банк **{amount_to_deposit}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Кошелёк",
        value=f"{new_wallet} {CURRENCY}",
        inline=False
    )
    embed.add_field(
        name="Банк",
        value=f"{new_bank} {CURRENCY}",
        inline=False
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed)


@bot.slash_command(name="withdraw", description="Снять деньги из банка")
async def withdraw(
    ctx: disnake.ApplicationCommandInteraction,
    amount: str = commands.Param(description="Сумма или 'all'")
):
    user_data = get_user_data(ctx.author.id)
    
    if amount.lower() == "all":
        amount_to_withdraw = user_data["bank"]
    else:
        try:
            amount_to_withdraw = int(amount)
        except ValueError:
            embed = disnake.Embed(
                title="Ошибка",
                description="Укажите число или 'all'",
                color=EMBED_COLOR
            )
            await safe_send(ctx, embed=embed, ephemeral=True)
            return
    
    if amount_to_withdraw <= 0:
        embed = disnake.Embed(
            title="Ошибка",
            description="Сумма должна быть больше 0",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    if user_data["bank"] < amount_to_withdraw:
        embed = disnake.Embed(
            title="Ошибка",
            description=f"Недостаточно денег в банке!",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    new_wallet = user_data["wallet"] + amount_to_withdraw
    new_bank = user_data["bank"] - amount_to_withdraw
    
    update_user_wallet(ctx.author.id, new_wallet)
    update_user_bank(ctx.author.id, new_bank)
    
    embed = disnake.Embed(
        title="Снятие денег",
        description=f"Вы сняли из банка **{amount_to_withdraw}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Кошелёк",
        value=f"{new_wallet} {CURRENCY}",
        inline=False
    )
    embed.add_field(
        name="Банк",
        value=f"{new_bank} {CURRENCY}",
        inline=False
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed)
