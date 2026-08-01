import os
import sys
import asyncio
import random
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import BOT_START_TIME, CURRENCY, DEV_ID, EMBED_COLOR, TOKEN, WORK_MAX, WORK_MIN
from phantycoon.data import ORES, PICKAXES, PRESTIGE_TOKEN_EMOJI, PRESTIGE_TOKEN_NAME, UPGRADES
from phantycoon.database import *
from phantycoon.shop_data import load_shop, save_shop
from phantycoon.interactions import safe_defer, safe_embed, safe_send
from phantycoon.progression import add_quest_rewards_to_embed, boost_multiplier, record_quest_event

# ==================== INVENTORY ====================

class InventorySelect(disnake.ui.Select):
    def __init__(self, user_id=None, items=None, author_id=None):
        self.user_id = user_id
        self.author_id = author_id
        options = []
        for item_name, quantity in (items or {"Inventory": 1}).items():
            if quantity > 0:
                label = f"{item_name} x{quantity}"
                if item_name == PRESTIGE_TOKEN_NAME:
                    label = f"{PRESTIGE_TOKEN_EMOJI} {label}"
                options.append(
                    disnake.SelectOption(
                        label=label,
                        value=item_name,
                        description=f"Quantity: {quantity}"
                    )
                )
        super().__init__(
            placeholder="Choose an item",
            options=options,
            custom_id="inventory_select"
        )
    
    async def callback(self, inter: disnake.MessageInteraction):
        if self.author_id is not None and inter.author.id != self.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return
        
        await safe_defer(inter, with_message=False)
        item_name = inter.values[0]
        inventory = get_user_inventory(self.user_id or inter.author.id)
        quantity = inventory.get(item_name, 0)
        
        if quantity <= 0:
            await safe_embed(inter, "Error", "You do not have this item.", ephemeral=True)
            return
        
        shop = load_shop()
        
        category = None
        for cat, items in shop.items():
            if item_name in items:
                category = cat
                break
        
        # Check whether this is ore
        is_ore = item_name in ORES
        is_pickaxe = item_name in PICKAXES
        
        embed = disnake.Embed(
            title=f"{item_name}",
            description=f"Quantity: {quantity} pcs.",
            color=EMBED_COLOR
        )

        if item_name == PRESTIGE_TOKEN_NAME:
            embed.description = (
                f"Quantity: {quantity} pcs.\n"
                "This prestige currency can only be spent in `/prestige shop`."
            )
            await safe_send(inter, embed=embed)
            return
        
        view = disnake.ui.View(timeout=None)
        
        if is_pickaxe:
            # For pickaxes: equip or sell
            view.add_item(disnake.ui.Button(
                label="Equip",
                style=disnake.ButtonStyle.primary,
                custom_id=f"use_{item_name}"
            ))
            view.add_item(disnake.ui.Button(
                label="Sell",
                style=disnake.ButtonStyle.primary,
                custom_id=f"sell_{item_name}"
            ))
        elif is_ore:
            # For ore: sell only
            view.add_item(disnake.ui.Button(
                label="Sell",
                style=disnake.ButtonStyle.primary,
                custom_id=f"sell_{item_name}"
            ))
        else:
            view.add_item(disnake.ui.Button(
                label="Sell",
                style=disnake.ButtonStyle.primary,
                custom_id=f"sell_{item_name}"
            ))
        await safe_send(inter, embed=embed, view=view)


@bot.slash_command(name="inventory", description="Show inventory")
async def inventory(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(default=None, description="User")
):
    target = user or ctx.author
    inventory = get_user_inventory(target.id)
    
    if not inventory:
        embed = disnake.Embed(
            title=f"Inventory {target.name}",
            description="Inventory is empty",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    items_list = []
    for item_name, quantity in inventory.items():
        if quantity > 0:
            if item_name in ORES:
                items_list.append(f"{ORES[item_name]['emoji']} {item_name} x{quantity}")
            elif item_name in PICKAXES:
                items_list.append(f"{PICKAXES[item_name]['emoji']} {item_name} x{quantity}")
            elif item_name == PRESTIGE_TOKEN_NAME:
                items_list.append(f"{PRESTIGE_TOKEN_EMOJI} {item_name} x{quantity}")
            else:
                items_list.append(f"{item_name} x{quantity}")
    
    if not items_list:
        embed = disnake.Embed(
            title=f"Inventory {target.name}",
            description="Inventory is empty",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    embed = disnake.Embed(
        title=f"Inventory {target.name}",
        description="\n".join(items_list),
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    if target.id == ctx.author.id:
        view = disnake.ui.View(timeout=None)
        view.add_item(InventorySelect(target.id, inventory, ctx.author.id))
        await safe_defer(ctx)
        await safe_send(ctx, embed=embed, view=view)
    else:
        await safe_defer(ctx)
        await safe_send(ctx, embed=embed)


# ==================== INVENTORY BUTTON HANDLERS ====================

@bot.listen("on_button_click")
async def inventory_button_handler(inter: disnake.MessageInteraction):
    if not inter.data.custom_id.startswith(("use_", "sell_")):
        return
    
    await safe_defer(inter, with_message=False)
    action, item_name = inter.data.custom_id.split("_", 1)
    
    inventory = get_user_inventory(inter.author.id)
    quantity = inventory.get(item_name, 0)
    
    if quantity <= 0:
        await safe_embed(inter, "Error", "You do not have this item.", ephemeral=True)
        return

    if item_name == PRESTIGE_TOKEN_NAME:
        await safe_embed(
            inter,
            "Error",
            f"{PRESTIGE_TOKEN_EMOJI} {PRESTIGE_TOKEN_NAME} can only be spent in `/prestige shop`.",
            ephemeral=True,
        )
        return
    
    shop = load_shop()
    
    if action == "use":
        # Check whether this is a pickaxe
        if item_name in PICKAXES:
            # Equip pickaxe
            update_current_pickaxe(inter.author.id, item_name)
            
            embed = disnake.Embed(
                title=f"{PICKAXES[item_name]['emoji']} {item_name}",
                description=f"You equipped **{item_name}**!",
                color=EMBED_COLOR
            )
            await safe_send(inter, embed=embed)
            return
        
        await safe_embed(inter, "Error", "This item cannot be used.", ephemeral=True)
            
    elif action == "sell":
        price = 0
        
        # Check whether this is ore
        if item_name in ORES:
            # Check upgrade Ore Miner
            user_data = get_user_data(inter.author.id)
            miner_level = user_data.get("miner_boost_level", 0)
            ore_bonus = 0
            if miner_level > 0:
                levels = UPGRADES["miner_boost"]["levels"]
                for i in range(miner_level):
                    ore_bonus += levels[i]["ore_bonus"]
            
            ore_data = ORES[item_name]
            base_price = random.randint(ore_data["price_min"], ore_data["price_max"])
            prestige_multiplier = get_prestige_ore_value_multiplier(user_data)
            clan_multiplier = get_clan_ore_bonus_multiplier(inter.author.id)
            price = int(base_price * (1 + ore_bonus / 100) * prestige_multiplier * clan_multiplier * boost_multiplier(inter.author.id, "prospector"))
        elif item_name in PICKAXES:
            # Pickaxe sale price is 50% of purchase price
            for category, items in shop.items():
                if item_name in items:
                    price = int(items[item_name]["price"] * 0.5)
                    break
        else:
            for category, items in shop.items():
                if item_name in items:
                    price = int(items[item_name]["price"] * 0.5)
                    break
        
        if price == 0:
            await safe_embed(inter, "Error", "This item cannot be sold.", ephemeral=True)
            return
        
        # Sell one item
        inventory[item_name] -= 1
        if inventory[item_name] <= 0:
            del inventory[item_name]
        update_user_inventory(inter.author.id, inventory)
        
        user_data = get_user_data(inter.author.id)
        new_wallet = user_data["wallet"] + price
        update_user_wallet(inter.author.id, new_wallet)
        
        embed = disnake.Embed(
            title="Sale",
            description=f"You sold {item_name} for {price} {CURRENCY}",
            color=EMBED_COLOR
        )
        if item_name in ORES:
            quest_rewards = record_quest_event(inter.author.id, "ore_sales", 1)
            quest_rewards += record_quest_event(inter.author.id, "ore_sale_value", price)
            add_quest_rewards_to_embed(embed, quest_rewards)
        await safe_send(inter, embed=embed)
