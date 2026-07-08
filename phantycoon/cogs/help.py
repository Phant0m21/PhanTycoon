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

# ==================== HELP ====================

class HelpSelect(disnake.ui.Select):
    def __init__(self, author_id):
        self.author_id = author_id
        options = [
            disnake.SelectOption(label="💸 Core", value="economy", description=""),
            disnake.SelectOption(label="🛠 Utilities", value="utils", description=""),
            disnake.SelectOption(label="👑 Administration", value="admin", description="")
        ]
        super().__init__(placeholder="Choose a category", options=options, custom_id="help_select")
    
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.author_id:
            await safe_send(inter, "❌ This is not your menu!", ephemeral=True)
            return
        
        category = inter.values[0]
        
        if category == "economy":
            embed = disnake.Embed(
                title="💸 Core",
                description="Economy commands",
                color=EMBED_COLOR
            )
            embed.add_field(name="/balance", value="Show balance", inline=False)
            embed.add_field(name="/work", value="Earn cash", inline=False)
            embed.add_field(name="/collect", value="Collect business income", inline=False)
            embed.add_field(name="/top", value="Show leaderboard", inline=False)
            embed.add_field(name="/shop", value="Open the shop", inline=False)
            embed.add_field(name="/buy", value="Buy an item", inline=False)
            embed.add_field(name="/inventory", value="Show inventory", inline=False)
            embed.add_field(name="/profile", value="Show profile", inline=False)
            embed.add_field(name="/coinflip", value="Flip a coin", inline=False)
            embed.add_field(name="/mine", value="Go mining", inline=False)
            embed.add_field(name="/shop_upgrades", value="Upgrades", inline=False)
            embed.add_field(name="/prestige_reset", value="Reset progress for prestige currency", inline=False)
            embed.add_field(name="/prestige_shop", value="Buy permanent prestige upgrades", inline=False)
            
        elif category == "utils":
            embed = disnake.Embed(
                title="🛠 Utilities",
                description="Utility commands",
                color=EMBED_COLOR
            )
            embed.add_field(name="/ping", value="Show technical info", inline=False)
            
        elif category == "admin":
            embed = disnake.Embed(
                title="👑 Administration",
                description="Administration commands",
                color=EMBED_COLOR
            )
            embed.add_field(name="/add_money", value="Give cash to a user", inline=False)
            embed.add_field(name="/remove_money", value="Remove cash from a user", inline=False)
            embed.add_field(name="/set_money", value="Set exact balance", inline=False)
            embed.add_field(name="/restart", value="Restart the bot (developer only)", inline=False)
        
        await safe_edit(inter, embed=embed, view=self.view)


class HelpView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(author_id))


@bot.slash_command(name="help", description="Show command list")
async def help(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="Bot Help",
        description="Choose a category below to view commands",
        color=EMBED_COLOR
    )
    view = HelpView(ctx.author.id)
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed, view=view)
