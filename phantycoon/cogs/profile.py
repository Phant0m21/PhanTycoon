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

# ==================== PROFILE ====================

class ProfileView(disnake.ui.View):
    def __init__(self, author_id, target_id, mode="profile"):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.target_id = target_id
        self.mode = mode
        self.message = None
        
        self.add_item(ProfileButton("Profile", "profile", disnake.ButtonStyle.primary if mode == "profile" else disnake.ButtonStyle.secondary))
        self.add_item(ProfileButton("Stats", "stats", disnake.ButtonStyle.primary if mode == "stats" else disnake.ButtonStyle.secondary))
    
    async def update_embed(self, inter: disnake.MessageInteraction):
        target = await inter.bot.fetch_user(self.target_id)
        user_data = get_user_data(self.target_id)
        
        if self.mode == "profile":
            embed = disnake.Embed(
                title=f"Profile {target.name}",
                color=EMBED_COLOR
            )
            
            total = user_data["wallet"] + user_data["bank"]
            
            embed.add_field(
                name="Prestige",
                value="0",
                inline=False
            )
            embed.add_field(
                name="Clan",
                value="No clan",
                inline=False
            )
            embed.add_field(
                name="Net worth",
                value=f"{total} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Wallet",
                value=f"{user_data['wallet']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Bank",
                value=f"{user_data['bank']} {CURRENCY}",
                inline=False
            )
            
            # Current pickaxe
            current_pickaxe = user_data.get("current_pickaxe", "Stone Pickaxe")
            pickaxe_emoji = PICKAXES.get(current_pickaxe, {}).get("emoji", "")
            embed.add_field(
                name="Pickaxe",
                value=f"{pickaxe_emoji} {current_pickaxe}",
                inline=False
            )
            
            # Upgrade levels
            time_level = user_data.get("time_management_level", 0)
            business_level = user_data.get("business_optimization_level", 0)
            miner_level = user_data.get("miner_boost_level", 0)
            
            embed.add_field(
                name="⏱️ Time Management",
                value=f"Level {time_level}/{UPGRADES['time_management']['max_level']}",
                inline=True
            )
            embed.add_field(
                name="🏢 Business Optimization",
                value=f"Level {business_level}/{UPGRADES['business_optimization']['max_level']}",
                inline=True
            )
            embed.add_field(
                name="⛏️ Ore Miner",
                value=f"Level {miner_level}/{UPGRADES['miner_boost']['max_level']}",
                inline=True
            )
            
            businesses = get_user_businesses(self.target_id)
            if businesses:
                embed.add_field(
                    name="Active businesses",
                    value="\n".join(businesses),
                    inline=False
                )
            else:
                embed.add_field(
                    name="Active businesses",
                    value="None",
                    inline=False
                )
            
            embed.set_thumbnail(url=target.display_avatar.url)
            
        else:  # stats
            embed = disnake.Embed(
                title=f"Stats {target.name}",
                color=EMBED_COLOR
            )
            
            registered_dt = datetime.fromisoformat(user_data["registered_at"])
            months = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            registered = f"{registered_dt.day} {months[registered_dt.month]} {registered_dt.year}"
            
            embed.add_field(
                name="Registered",
                value=registered,
                inline=False
            )
            embed.add_field(
                name="Total earned",
                value=f"{user_data['total_earned']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Total spent",
                value=f"{user_data['total_spent']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Earned from /work",
                value=f"{user_data['work_earned']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Earned from /collect",
                value=f"{user_data['collect_earned']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Jobs completed",
                value=f"{user_data['work_count']}",
                inline=False
            )
            embed.add_field(
                name="Minigames played",
                value=f"{user_data['games_played']}",
                inline=False
            )
            
            embed.set_thumbnail(url=target.display_avatar.url)
        
        self.clear_items()
        self.add_item(ProfileButton("Profile", "profile", disnake.ButtonStyle.primary if self.mode == "profile" else disnake.ButtonStyle.secondary))
        self.add_item(ProfileButton("Stats", "stats", disnake.ButtonStyle.primary if self.mode == "stats" else disnake.ButtonStyle.secondary))
        
        await safe_edit(inter, embed=embed, view=self)
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if not self.message:
            return
        try:
            await self.message.edit(view=self)
        except disnake.HTTPException:
            pass


class ProfileButton(disnake.ui.Button):
    def __init__(self, label, mode, style):
        super().__init__(label=label, style=style, custom_id=f"profile_{mode}")
        self.mode = mode
    
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author_id:
            await safe_send(inter, "❌ This is not your menu!", ephemeral=True)
            return
        
        await safe_defer(inter, with_message=False)
        self.view.mode = self.mode
        await self.view.update_embed(inter)


@bot.slash_command(name="profile", description="Show user profile")
async def profile(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(default=None, description="User")
):
    target = user or ctx.author
    user_data = get_user_data(target.id)
    
    embed = disnake.Embed(
        title=f"Profile {target.name}",
        color=EMBED_COLOR
    )
    
    total = user_data["wallet"] + user_data["bank"]
    
    embed.add_field(
        name="Prestige",
        value="0",
        inline=False
    )
    embed.add_field(
        name="Clan",
        value="No clan",
        inline=False
    )
    embed.add_field(
        name="Net worth",
        value=f"{total} {CURRENCY}",
        inline=False
    )
    embed.add_field(
        name="Wallet",
        value=f"{user_data['wallet']} {CURRENCY}",
        inline=False
    )
    embed.add_field(
        name="Bank",
        value=f"{user_data['bank']} {CURRENCY}",
        inline=False
    )
    
    # Current pickaxe
    current_pickaxe = user_data.get("current_pickaxe", "Stone Pickaxe")
    pickaxe_emoji = PICKAXES.get(current_pickaxe, {}).get("emoji", "")
    embed.add_field(
        name="Pickaxe",
        value=f"{pickaxe_emoji} {current_pickaxe}",
        inline=False
    )
    
    # Upgrade levels
    time_level = user_data.get("time_management_level", 0)
    business_level = user_data.get("business_optimization_level", 0)
    miner_level = user_data.get("miner_boost_level", 0)
    
    embed.add_field(
        name="⏱️ Time Management",
        value=f"Level {time_level}/{UPGRADES['time_management']['max_level']}",
        inline=True
    )
    embed.add_field(
        name="🏢 Business Optimization",
        value=f"Level {business_level}/{UPGRADES['business_optimization']['max_level']}",
        inline=True
    )
    embed.add_field(
        name="⛏️ Ore Miner",
        value=f"Level {miner_level}/{UPGRADES['miner_boost']['max_level']}",
        inline=True
    )
    
    businesses = get_user_businesses(target.id)
    if businesses:
        embed.add_field(
            name="Active businesses",
            value="\n".join(businesses),
            inline=False
        )
    else:
        embed.add_field(
            name="Active businesses",
            value="None",
            inline=False
        )
    
    embed.set_thumbnail(url=target.display_avatar.url)
    
    view = ProfileView(ctx.author.id, target.id, mode="profile")
    
    await safe_defer(ctx)
    view.message = await safe_send(ctx, embed=embed, view=view)
