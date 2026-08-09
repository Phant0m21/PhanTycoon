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
from phantycoon.interactions import safe_defer, safe_edit, safe_embed, safe_send
from phantycoon.cogs.maintenance import block_if_maintenance_active
from phantycoon.progression import add_quest_rewards_to_embed, record_quest_event

# ==================== SHOP ====================

class ShopSelect(disnake.ui.Select):
    def __init__(self, author_id):
        self.author_id = author_id
        options = [
            disnake.SelectOption(label="🏢 Businesses", value="business", description="Passive income"),
            disnake.SelectOption(label="⛏️ Pickaxes", value="pickaxes", description="Upgrade mining")
        ]
        super().__init__(placeholder="Choose a category", options=options, custom_id="shop_select")
    
    async def callback(self, inter: disnake.MessageInteraction):
        if await block_if_maintenance_active(inter):
            return
        if self.author_id is not None and inter.author.id != self.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return
        
        await safe_defer(inter, with_message=False)
        category = inter.values[0]
        shop = load_shop()
        items = shop.get(category, {})
        user_businesses = get_user_businesses(inter.author.id)
        user_data = get_user_data(inter.author.id)
        current_pickaxe = user_data.get("current_pickaxe", "Stone Pickaxe")
        
        if category == "business":
            lines = []
            embed = disnake.Embed(
                title="🏢 Businesses",
                description="",
                color=EMBED_COLOR
            )
            for name, data in items.items():
                check = " ✅" if name in user_businesses else ""
                lines.append(f"{data['emoji']} **{name}**{check}\nPrice: **{data['price']:,}{CURRENCY}**\nIncome every 6 hours: **+{data['income']:,}{CURRENCY}**")
            embed.description = "\n".join(lines)
                
        elif category == "pickaxes":
            lines = []
            embed = disnake.Embed(
                title="⛏️ Pickaxes",
                description="",
                color=EMBED_COLOR
            )
            for name, data in items.items():
                pickaxe_data = PICKAXES.get(name, {})
                if not pickaxe_data:
                    continue
                check = " ✅" if name == current_pickaxe else ""
                lines.append(f"{pickaxe_data.get('emoji', '')} **{name}**{check}\nPrice: **{data['price']:,}{CURRENCY}**")
            embed.description = "\n".join(lines)
                
        embed.set_footer(text="Purchase with /buy")
        await safe_edit(inter, embed=embed, view=self.view)


class ShopView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.add_item(ShopSelect(author_id))


@bot.slash_command(name="shop", description="Shop commands")
async def shop(ctx: disnake.ApplicationCommandInteraction):
    pass


@shop.sub_command(name="open", description="Open the shop")
async def shop_open(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="Shop",
        description="Choose a category below",
        color=EMBED_COLOR
    )
    view = ShopView(ctx.author.id)
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed, view=view)


@bot.slash_command(name="buy", description="Buy an item")
async def buy(
    ctx: disnake.ApplicationCommandInteraction,
    name: str = commands.Param(description="Item name"),
    quantity: int = commands.Param(default=1, gt=0, description="Quantity")
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
            title="Error",
            description="Item not found. Use `/shop open` to browse the shop.",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    item_data = shop[found_category][found_item]
    total_price = item_data["price"] * quantity
    
    user_data = get_user_data(ctx.author.id)
    if user_data["wallet"] < total_price:
        embed = disnake.Embed(
            title="Error",
            description=f"Not enough cash! Need: {total_price} {CURRENCY}",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return

    if found_category in {"business", "pickaxes"} and quantity != 1:
        embed = disnake.Embed(
            title="Error",
            description="This item can only be bought one at a time.",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    if found_category == "business":
        businesses = get_user_businesses(ctx.author.id)
        if found_item in businesses:
            embed = disnake.Embed(
                title="Error",
                description="You already own this business.",
                color=EMBED_COLOR
            )
            await safe_send(ctx, embed=embed, ephemeral=True)
            return
        
        await safe_defer(ctx)
        update_user_wallet(ctx.author.id, user_data["wallet"] - total_price)
        update_stats(ctx.author.id, total_spent=total_price)
        add_business(ctx.author.id, found_item)
        
        embed = disnake.Embed(
            title="Purchase",
            description=f"{ctx.author.mention} bought **{found_item}** for {total_price} {CURRENCY}",
            color=EMBED_COLOR
        )
        embed.add_field(
            name="Income",
            value=f"{item_data['income']} {CURRENCY} every 6 hours",
            inline=False
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
    elif found_category == "pickaxes":
        # Check whether the pickaxe is already owned
        inventory = get_user_inventory(ctx.author.id)
        if found_item in inventory and inventory[found_item] > 0:
            embed = disnake.Embed(
                title="Error",
                description="You already own this pickaxe.",
                color=EMBED_COLOR
            )
            await safe_send(ctx, embed=embed, ephemeral=True)
            return
        
        await safe_defer(ctx)
        update_user_wallet(ctx.author.id, user_data["wallet"] - total_price)
        update_stats(ctx.author.id, total_spent=total_price)

        # Add pickaxe to inventory
        inventory[found_item] = inventory.get(found_item, 0) + quantity
        update_user_inventory(ctx.author.id, inventory)
        
        embed = disnake.Embed(
            title="Purchase",
            description=f"{ctx.author.mention} bought **{found_item}** for {total_price} {CURRENCY}",
            color=EMBED_COLOR
        )
        embed.add_field(
            name="Now in inventory",
            value=f"{inventory[found_item]} pcs.",
            inline=False
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
    add_quest_rewards_to_embed(embed, record_quest_event(ctx.author.id, "cash_spent", total_price))
    await safe_send(ctx, embed=embed)
