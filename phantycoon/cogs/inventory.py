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

# ==================== INVENTORY ====================

class InventorySelect(disnake.ui.Select):
    def __init__(self, user_id, items, author_id):
        self.user_id = user_id
        self.author_id = author_id
        options = []
        for item_name, quantity in items.items():
            if quantity > 0:
                options.append(
                    disnake.SelectOption(
                        label=f"{item_name} x{quantity}",
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
        if inter.author.id != self.author_id:
            await safe_send(inter, "❌ This is not your menu!", ephemeral=True)
            return
        
        await safe_defer(inter, ephemeral=True)
        item_name = inter.values[0]
        inventory = get_user_inventory(self.user_id)
        quantity = inventory.get(item_name, 0)
        
        if quantity <= 0:
            await safe_send(inter, "❌ You do not have this item!", ephemeral=True)
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
        
        view = disnake.ui.View()
        
        if is_pickaxe:
            # For pickaxes: equip or sell
            view.add_item(disnake.ui.Button(
                label="Equip",
                style=disnake.ButtonStyle.green,
                custom_id=f"use_{item_name}"
            ))
            view.add_item(disnake.ui.Button(
                label="Sell",
                style=disnake.ButtonStyle.red,
                custom_id=f"sell_{item_name}"
            ))
        elif is_ore:
            # For ore: sell only
            view.add_item(disnake.ui.Button(
                label="Sell",
                style=disnake.ButtonStyle.red,
                custom_id=f"sell_{item_name}"
            ))
        elif category == "consumables" and category != "other":
            view.add_item(disnake.ui.Button(
                label="Use",
                style=disnake.ButtonStyle.green,
                custom_id=f"use_{item_name}"
            ))
            view.add_item(disnake.ui.Button(
                label="Sell",
                style=disnake.ButtonStyle.red,
                custom_id=f"sell_{item_name}"
            ))
        elif category == "other":
            view.add_item(disnake.ui.Button(
                label="Sell",
                style=disnake.ButtonStyle.red,
                custom_id=f"sell_{item_name}"
            ))
        else:
            view.add_item(disnake.ui.Button(
                label="Sell",
                style=disnake.ButtonStyle.red,
                custom_id=f"sell_{item_name}"
            ))
        
        await safe_send(inter, embed=embed, view=view, ephemeral=True)


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
        await safe_defer(ctx)
        await safe_send(ctx, embed=embed)
        return
    
    items_list = []
    for item_name, quantity in inventory.items():
        if quantity > 0:
            if item_name in ORES:
                items_list.append(f"{ORES[item_name]['emoji']} {item_name} x{quantity}")
            elif item_name in PICKAXES:
                items_list.append(f"{PICKAXES[item_name]['emoji']} {item_name} x{quantity}")
            else:
                items_list.append(f"{item_name} x{quantity}")
    
    embed = disnake.Embed(
        title=f"Inventory {target.name}",
        description="\n".join(items_list),
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    if target.id == ctx.author.id:
        view = disnake.ui.View()
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
    
    await safe_defer(inter, ephemeral=True)
    action, item_name = inter.data.custom_id.split("_", 1)
    
    inventory = get_user_inventory(inter.author.id)
    quantity = inventory.get(item_name, 0)
    
    if quantity <= 0:
        await safe_send(inter, "❌ You do not have this item!", ephemeral=True)
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
            await safe_send(inter, embed=embed, ephemeral=True)
            return
        
        if item_name == "Energy Drink":
            user_data = get_user_data(inter.author.id)
            if user_data.get("last_work"):
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET last_work = ? WHERE user_id = ?", (None, str(inter.author.id)))
                conn.commit()
                conn.close()
            
            inventory[item_name] -= 1
            if inventory[item_name] <= 0:
                del inventory[item_name]
            update_user_inventory(inter.author.id, inventory)
            
            embed = disnake.Embed(
                title="Energy Drink",
                description="`/work` cooldown reset. You can work again.",
                color=EMBED_COLOR
            )
            await safe_send(inter, embed=embed, ephemeral=True)
            
        elif item_name == "Vitamins":
            if inter.author.id in active_buffs:
                active_buffs[inter.author.id]["remaining"] += 3
            else:
                active_buffs[inter.author.id] = {"remaining": 3}
            
            inventory[item_name] -= 1
            if inventory[item_name] <= 0:
                del inventory[item_name]
            update_user_inventory(inter.author.id, inventory)
            
            embed = disnake.Embed(
                title="Vitamins",
                description="Vitamin boost activated. Your next 3 work shifts pay +45%.",
                color=EMBED_COLOR
            )
            await safe_send(inter, embed=embed, ephemeral=True)
            
        elif item_name == "Insurance":
            embed = disnake.Embed(
                title="Insurance",
                description="Insurance is used automatically after a minigame loss and refunds 30% of the bet.",
                color=EMBED_COLOR
            )
            await safe_send(inter, embed=embed, ephemeral=True)
            
        else:
            await safe_send(inter, "❌ This item cannot be used", ephemeral=True)
            
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
            price = int(base_price * (1 + ore_bonus / 100))
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
            await safe_send(inter, "❌ This item cannot be sold", ephemeral=True)
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
        await safe_send(inter, embed=embed, ephemeral=True)
