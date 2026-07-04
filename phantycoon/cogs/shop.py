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

# ==================== МАГАЗИН ====================

class ShopSelect(disnake.ui.Select):
    def __init__(self, author_id):
        self.author_id = author_id
        options = [
            disnake.SelectOption(label="🏢 Бизнесы", value="business", description="Пассивный доход"),
            disnake.SelectOption(label="⚡ Расходники", value="consumables", description="Одноразовые предметы"),
            disnake.SelectOption(label="⛏️ Кирки", value="pickaxes", description="Улучшайте добычу"),
            disnake.SelectOption(label="💎 Другое", value="other", description="Визуальные предметы")
        ]
        super().__init__(placeholder="Выберите категорию", options=options, custom_id="shop_select")
    
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        category = inter.values[0]
        shop = load_shop()
        items = shop.get(category, {})
        user_businesses = get_user_businesses(inter.author.id)
        user_data = get_user_data(inter.author.id)
        current_pickaxe = user_data.get("current_pickaxe", "Каменная кирка")
        
        if category == "business":
            embed = disnake.Embed(
                title="🏢 Бизнесы",
                description="Приносят пассивный доход раз в 6 часов через `/collect`",
                color=EMBED_COLOR
            )
            for name, data in items.items():
                check = " ✅" if name in user_businesses else ""
                embed.add_field(
                    name=f"{data['emoji']} {name} - {data['price']} {CURRENCY}{check}",
                    value=f"Приносит {data['income']} {CURRENCY} раз в 6 часов",
                    inline=False
                )
                
        elif category == "consumables":
            embed = disnake.Embed(
                title="⚡ Расходники",
                description="Одноразовые предметы для инвентаря",
                color=EMBED_COLOR
            )
            for name, data in items.items():
                embed.add_field(
                    name=f"{data['emoji']} {name} - {data['price']} {CURRENCY}",
                    value=data.get("description", ""),
                    inline=False
                )
        
        elif category == "pickaxes":
            embed = disnake.Embed(
                title="⛏️ Кирки",
                description="Улучшайте свою кирку для более эффективной добычи!",
                color=EMBED_COLOR
            )
            for name, data in items.items():
                pickaxe_data = PICKAXES.get(name, {})
                if not pickaxe_data:
                    continue
                check = " ✅" if name == current_pickaxe else ""
                ores_list = ", ".join(pickaxe_data.get("ores", []))
                embed.add_field(
                    name=f"{pickaxe_data.get('emoji', '')} {name} - {data['price']} {CURRENCY}{check}",
                    value=f"Кулдаун: {pickaxe_data.get('cooldown', 0)} сек\nРуда: {ores_list}",
                    inline=False
                )
                
        elif category == "other":
            embed = disnake.Embed(
                title="💎 Другое",
                description="Визуальные предметы для профиля",
                color=EMBED_COLOR
            )
            for name, data in items.items():
                embed.add_field(
                    name=f"{data['emoji']} {name} - {data['price']} {CURRENCY}",
                    value=data.get("description", ""),
                    inline=False
                )
        
        embed.set_footer(text="Для покупки используйте `/buy`")
        await inter.response.edit_message(embed=embed, view=self.view)


class ShopView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.add_item(ShopSelect(author_id))


@bot.slash_command(name="shop", description="Открыть магазин")
async def shop(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="Магазин бота",
        description="Выберите категорию в меню ниже",
        color=EMBED_COLOR
    )
    view = ShopView(ctx.author.id)
    await ctx.response.defer()
    await ctx.followup.send(embed=embed, view=view)


@bot.slash_command(name="buy", description="Купить товар")
async def buy(
    ctx: disnake.ApplicationCommandInteraction,
    name: str = commands.Param(description="Название товара"),
    quantity: int = commands.Param(default=1, gt=0, description="Количество")
):
    shop = load_shop()
    
    found_item = None
    found_category = None
    
    for category, items in shop.items():
        for item_name, item_data in items.items():
            if name.lower() in item_name.lower():
                found_item = item_name
                found_category = category
                break
        if found_item:
            break
    
    if not found_item:
        embed = disnake.Embed(
            title="Ошибка",
            description="Товар не найден! Используйте /shop для просмотра товаров",
            color=EMBED_COLOR
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    item_data = shop[found_category][found_item]
    total_price = item_data["price"] * quantity
    
    user_data = get_user_data(ctx.author.id)
    if user_data["wallet"] < total_price:
        embed = disnake.Embed(
            title="Ошибка",
            description=f"Недостаточно денег! Нужно: {total_price} {CURRENCY}",
            color=EMBED_COLOR
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return

    if found_category in {"business", "pickaxes"} and quantity != 1:
        embed = disnake.Embed(
            title="Ошибка",
            description="Этот товар можно купить только в количестве 1 шт.",
            color=EMBED_COLOR
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    
    if found_category == "business":
        businesses = get_user_businesses(ctx.author.id)
        if found_item in businesses:
            embed = disnake.Embed(
                title="Ошибка",
                description="У вас уже есть этот бизнес!",
                color=EMBED_COLOR
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        
        update_user_wallet(ctx.author.id, user_data["wallet"] - total_price)
        update_stats(ctx.author.id, total_spent=total_price)
        add_business(ctx.author.id, found_item)
        
        embed = disnake.Embed(
            title="Покупка",
            description=f"{ctx.author.mention} купил **{found_item}** за {total_price} {CURRENCY}",
            color=EMBED_COLOR
        )
        embed.add_field(
            name="Доход",
            value=f"{item_data['income']} {CURRENCY} раз в 6 часов",
            inline=False
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
    elif found_category == "consumables":
        update_user_wallet(ctx.author.id, user_data["wallet"] - total_price)
        update_stats(ctx.author.id, total_spent=total_price)

        inventory = get_user_inventory(ctx.author.id)
        inventory[found_item] = inventory.get(found_item, 0) + quantity
        update_user_inventory(ctx.author.id, inventory)
        
        embed = disnake.Embed(
            title="Покупка",
            description=f"{ctx.author.mention} купил **{found_item}** x{quantity} за {total_price} {CURRENCY}",
            color=EMBED_COLOR
        )
        embed.add_field(
            name="Теперь в инвентаре",
            value=f"{inventory[found_item]} шт.",
            inline=False
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
    elif found_category == "pickaxes":
        # Проверяем, не куплена ли уже кирка
        inventory = get_user_inventory(ctx.author.id)
        if found_item in inventory and inventory[found_item] > 0:
            embed = disnake.Embed(
                title="Ошибка",
                description="У вас уже есть эта кирка!",
                color=EMBED_COLOR
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        
        update_user_wallet(ctx.author.id, user_data["wallet"] - total_price)
        update_stats(ctx.author.id, total_spent=total_price)

        # Добавляем кирку в инвентарь
        inventory[found_item] = inventory.get(found_item, 0) + quantity
        update_user_inventory(ctx.author.id, inventory)
        
        embed = disnake.Embed(
            title="Покупка",
            description=f"{ctx.author.mention} купил **{found_item}** за {total_price} {CURRENCY}",
            color=EMBED_COLOR
        )
        embed.add_field(
            name="Теперь в инвентаре",
            value=f"{inventory[found_item]} шт.",
            inline=False
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
    else:  # other
        update_user_wallet(ctx.author.id, user_data["wallet"] - total_price)
        update_stats(ctx.author.id, total_spent=total_price)

        inventory = get_user_inventory(ctx.author.id)
        inventory[found_item] = inventory.get(found_item, 0) + quantity
        update_user_inventory(ctx.author.id, inventory)
        
        embed = disnake.Embed(
            title="Покупка",
            description=f"{ctx.author.mention} купил **{found_item}** x{quantity} за {total_price} {CURRENCY}",
            color=EMBED_COLOR
        )
        embed.add_field(
            name="Теперь в инвентаре",
            value=f"{inventory[found_item]} шт.",
            inline=False
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    await ctx.response.defer()
    await ctx.followup.send(embed=embed)
