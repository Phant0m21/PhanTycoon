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

# ==================== MINE ====================

class MineView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id
    
    @disnake.ui.button(label="Копать снова", style=disnake.ButtonStyle.primary)
    async def mine_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем кулдаун
        can, next_time, cooldown = can_mine(inter.author.id)
        if not can:
            remaining = next_time - datetime.now(timezone.utc)
            wait_seconds = max(1, int(remaining.total_seconds()))
            embed = disnake.Embed(
                title="Шахта",
                description=f"Вы слишком часто копаете. Подождите **{wait_seconds} сек.**",
                color=EMBED_COLOR
            )
            embed.set_thumbnail(url=inter.author.display_avatar.url)
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        await inter.response.defer()
        
        # Выполняем добычу
        user_data = get_user_data(inter.author.id)
        pickaxe_name = user_data.get("current_pickaxe", "Каменная кирка")
        pickaxe_emoji = PICKAXES.get(pickaxe_name, {}).get("emoji", "")
        
        ore_name, amount = get_mine_result(pickaxe_name)
        
        # Добавляем руду в инвентарь
        inventory = get_user_inventory(inter.author.id)
        inventory[ore_name] = inventory.get(ore_name, 0) + amount
        update_user_inventory(inter.author.id, inventory)
        
        # Обновляем время добычи
        update_last_mine(inter.author.id)
        
        # Отправляем результат с кнопками
        embed = disnake.Embed(
            title="Шахта",
            description=f"{inter.author.mention} нашёл:\n{ORES[ore_name]['emoji']} {ore_name} x{amount}\n\nКирка: {pickaxe_emoji} {pickaxe_name}",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        
        # Создаём новый View с кнопками для нового сообщения
        view = MineView(inter.author.id)
        await inter.followup.send(embed=embed, view=view)
    
    @disnake.ui.button(label="Продать руду", style=disnake.ButtonStyle.success)
    async def sell_ores_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await inter.response.defer()
        
        inventory = get_user_inventory(inter.author.id)
        
        total_earned = 0
        sold_items = []
        
        # Проверяем апгрейд Майнер руды
        user_data = get_user_data(inter.author.id)
        miner_level = user_data.get("miner_boost_level", 0)
        ore_bonus = 0
        if miner_level > 0:
            levels = UPGRADES["miner_boost"]["levels"]
            for i in range(miner_level):
                ore_bonus += levels[i]["ore_bonus"]
        
        for ore_name, quantity in list(inventory.items()):
            if ore_name in ORES and quantity > 0:
                ore_data = ORES[ore_name]
                base_price = random.randint(ore_data["price_min"], ore_data["price_max"])
                price = int(base_price * (1 + ore_bonus / 100))
                earned = price * quantity
                total_earned += earned
                sold_items.append(f"{ORES[ore_name]['emoji']} {ore_name} x{quantity} = {earned} {CURRENCY}")
                del inventory[ore_name]
        
        if total_earned == 0:
            embed = disnake.Embed(
                title="Продажа руды",
                description="У вас нет руды для продажи!",
                color=EMBED_COLOR
            )
            embed.set_thumbnail(url=inter.author.display_avatar.url)
            await inter.followup.send(embed=embed, ephemeral=True)
            return
        
        update_user_inventory(inter.author.id, inventory)
        user_data = get_user_data(inter.author.id)
        update_user_wallet(inter.author.id, user_data["wallet"] + total_earned)
        update_stats(inter.author.id, total_earned=total_earned)
        
        embed = disnake.Embed(
            title="Продажа руды",
            description="\n".join(sold_items) + f"\n\n**Итого: {total_earned} {CURRENCY}**",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        
        # Создаём новый View с кнопками для нового сообщения
        view = MineView(inter.author.id)
        await inter.followup.send(embed=embed, view=view)


@bot.slash_command(name="mine", description="Пойти в шахту")
async def mine(ctx: disnake.ApplicationCommandInteraction):
    await ctx.response.defer()
    
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    
    # Проверяем кулдаун
    can, next_time, cooldown = can_mine(user_id)
    if not can:
        remaining = next_time - datetime.now(timezone.utc)
        wait_seconds = max(1, int(remaining.total_seconds()))
        embed = disnake.Embed(
            title="Шахта",
            description=f"Вы слишком часто копаете. Подождите **{wait_seconds} сек.**",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.followup.send(embed=embed)
        return
    
    pickaxe_name = user_data.get("current_pickaxe", "Каменная кирка")
    pickaxe_emoji = PICKAXES.get(pickaxe_name, {}).get("emoji", "")
    
    # Выполняем добычу
    ore_name, amount = get_mine_result(pickaxe_name)
    
    # Добавляем руду в инвентарь
    inventory = get_user_inventory(user_id)
    inventory[ore_name] = inventory.get(ore_name, 0) + amount
    update_user_inventory(user_id, inventory)
    
    # Обновляем время добычи
    update_last_mine(user_id)
    
    # Отправляем результат с кнопками
    embed = disnake.Embed(
        title="Шахта",
        description=f"{ctx.author.mention} нашёл:\n{ORES[ore_name]['emoji']} {ore_name} x{amount}\n\nКирка: {pickaxe_emoji} {pickaxe_name}",
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    view = MineView(ctx.author.id)
    await ctx.followup.send(embed=embed, view=view)
