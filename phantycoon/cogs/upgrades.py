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
from phantycoon.interactions import safe_defer, safe_embed, safe_send
from phantycoon.cogs.shop import shop
from phantycoon.progression import add_quest_rewards_to_embed, record_quest_event

# ==================== SHOP UPGRADES ====================

class UpgradesView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.message = None
        if author_id is None:
            for upgrade_id, upgrade_data in UPGRADES.items():
                self.add_item(UpgradeButton(upgrade_id, upgrade_data["name"], disnake.ButtonStyle.primary, False))
        else:
            self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        user_data = get_user_data(self.author_id)
        
        for upgrade_id, upgrade_data in UPGRADES.items():
            current_level = user_data.get(f"{upgrade_id}_level", 0)
            max_level = upgrade_data["max_level"]
            is_max = current_level >= max_level
            
            if is_max:
                label = f"{upgrade_data['name']} ✅ MAX"
                style = disnake.ButtonStyle.primary
            else:
                next_level = upgrade_data["levels"][current_level]
                label = f"{upgrade_data['name']} ({current_level}/{max_level}) - {next_level['price']}{CURRENCY}"
                style = disnake.ButtonStyle.primary
            
            self.add_item(UpgradeButton(
                upgrade_id=upgrade_id,
                label=label,
                style=style,
                disabled=False
            ))
    
    async def update_embed(self, inter: disnake.MessageInteraction, notice=None, quest_rewards=None):
        user_data = get_user_data(self.author_id)
        
        embed = disnake.Embed(
            title="Upgrades",
            description=f"Balance: **{user_data['wallet']:,}{CURRENCY}**" + (f" • {notice}" if notice else ""),
            color=EMBED_COLOR
        )
        
        for upgrade_id, upgrade_data in UPGRADES.items():
            current_level = user_data.get(f"{upgrade_id}_level", 0)
            max_level = upgrade_data["max_level"]
            
            if current_level >= max_level:
                status = "MAX LEVEL"
            else:
                next_level = upgrade_data["levels"][current_level]
                price = next_level["price"]
                status = f"Level {current_level}/{max_level} → Next: {price} {CURRENCY}"
            
            # Effect description
            if upgrade_id == "time_management":
                effect_desc = "Reduces /work and /mine cooldowns"
            elif upgrade_id == "business_optimization":
                effect_desc = "Increases business income"
            elif upgrade_id == "miner_boost":
                effect_desc = "Increases ore sale value"
            
            embed.add_field(
                name=f"{upgrade_data['name']}",
                value=f"{effect_desc}\n{status}",
                inline=False
            )
        
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        add_quest_rewards_to_embed(embed, quest_rewards or [])
        
        self.update_buttons()
        await safe_send(inter, embed=embed, view=UpgradesView(inter.author.id))
    
class UpgradeButton(disnake.ui.Button):
    def __init__(self, upgrade_id, label, style, disabled):
        super().__init__(
            label=label,
            style=style,
            custom_id=f"upgrade_{upgrade_id}",
            disabled=disabled
        )
        self.upgrade_id = upgrade_id
    
    async def callback(self, inter: disnake.MessageInteraction):
        if self.view.author_id is not None and inter.author.id != self.view.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return
        
        user_data = get_user_data(inter.author.id)
        current_level = user_data.get(f"{self.upgrade_id}_level", 0)
        upgrade_data = UPGRADES[self.upgrade_id]
        
        if current_level >= upgrade_data["max_level"]:
            embed = disnake.Embed(
                title="Error",
                description="This upgrade is already maxed.",
                color=EMBED_COLOR
            )
            await safe_send(inter, embed=embed, ephemeral=True)
            return
        
        next_level = upgrade_data["levels"][current_level]
        price = next_level["price"]
        
        if user_data["wallet"] < price:
            embed = disnake.Embed(
                title="Error",
                description=f"Not enough cash! Need: {price} {CURRENCY}",
                color=EMBED_COLOR
            )
            await safe_send(inter, embed=embed, ephemeral=True)
            return
        
        await safe_defer(inter, with_message=False)
        # Charge wallet
        new_wallet = user_data["wallet"] - price
        update_user_wallet(inter.author.id, new_wallet)
        
        # Increase level
        new_level = current_level + 1
        update_upgrade_level(inter.author.id, f"{self.upgrade_id}_level", new_level)
        
        quest_rewards = record_quest_event(inter.author.id, "cash_spent", price)
        quest_rewards += record_quest_event(inter.author.id, "upgrades_bought", 1)
        notice = f"Purchased {upgrade_data['name']} L{new_level}"
        if self.view.author_id is None:
            await UpgradesView(inter.author.id).update_embed(inter, notice, quest_rewards)
        else:
            await self.view.update_embed(inter, notice, quest_rewards)


@shop.sub_command(name="upgrades", description="Buy passive upgrades")
async def shop_upgrades(ctx: disnake.ApplicationCommandInteraction):
    await safe_defer(ctx)
    
    user_data = get_user_data(ctx.author.id)
    
    embed = disnake.Embed(
        title="Upgrades",
        description=f"Balance: **{user_data['wallet']:,}{CURRENCY}**",
        color=EMBED_COLOR
    )
    
    for upgrade_id, upgrade_data in UPGRADES.items():
        current_level = user_data.get(f"{upgrade_id}_level", 0)
        max_level = upgrade_data["max_level"]
        
        if current_level >= max_level:
            status = "MAX LEVEL"
        else:
            next_level = upgrade_data["levels"][current_level]
            price = next_level["price"]
            status = f"Level {current_level}/{max_level} → Next: {price} {CURRENCY}"
        
        # Effect description
        if upgrade_id == "time_management":
            effect_desc = "Reduces /work and /mine cooldowns"
        elif upgrade_id == "business_optimization":
            effect_desc = "Increases business income"
        elif upgrade_id == "miner_boost":
            effect_desc = "Increases ore sale value"
        
        embed.add_field(
            name=f"{upgrade_data['name']}",
            value=f"{effect_desc}\n{status}",
            inline=False
        )
    
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    view = UpgradesView(ctx.author.id)
    view.message = await safe_send(ctx, embed=embed, view=view)
