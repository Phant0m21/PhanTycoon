import os
import sys
import asyncio
import random
import re
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import BOT_START_TIME, CURRENCY, DEV_ID, EMBED_COLOR, TOKEN, WORK_MAX, WORK_MIN
from phantycoon.data import ORES, PICKAXES, UPGRADES
from phantycoon.database import *
from phantycoon.shop_data import load_shop, save_shop
from phantycoon.interactions import safe_defer, safe_edit, safe_embed, safe_send

TOP_SORT_COLUMNS = {
    "balance",
    "total_earned",
    "total_spent",
    "work_earned",
    "collect_earned",
    "work_count",
    "games_played",
    "prestige_level",
}

# ==================== LEADERBOARD WITH MODE AND SORTING ====================

class TopSelect(disnake.ui.Select):
    def __init__(self, author_id, mode="global", sort_by="balance"):
        self.author_id = author_id
        self.mode = mode
        self.sort_by = sort_by
        
        options = [
            disnake.SelectOption(
                label="Balance",
                value="balance",
                description="Current balance",
                emoji="💰"
            ),
            disnake.SelectOption(
                label="Total earned",
                value="total_earned",
                description="Total earned",
                emoji="💵"
            ),
            disnake.SelectOption(
                label="Total spent",
                value="total_spent",
                description="Total spent",
                emoji="💸"
            ),
            disnake.SelectOption(
                label="Earned from jobs",
                value="work_earned",
                description="Earned through /work",
                emoji="⚒️"
            ),
            disnake.SelectOption(
                label="Earned from businesses",
                value="collect_earned",
                description="Earned from businesses",
                emoji="🏢"
            ),
            disnake.SelectOption(
                label="Jobs completed",
                value="work_count",
                description="Jobs completed",
                emoji="📊"
            ),
            disnake.SelectOption(
                label="Minigames played",
                value="games_played",
                description="Minigames played",
                emoji="🎮"
            ),
            disnake.SelectOption(
                label="Prestige",
                value="prestige_level",
                description="Prestige level",
                emoji="🦘"
            )
        ]
        super().__init__(
            placeholder="Choose sorting",
            options=options,
            custom_id="top_sort_select"
        )
    
    async def callback(self, inter: disnake.MessageInteraction):
        if self.author_id is not None and inter.author.id != self.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return
        
        await safe_defer(inter, with_message=False)
        self.sort_by = inter.values[0]
        if self.author_id is None:
            mode = "server" if inter.message.embeds and inter.message.embeds[0].title.startswith("Server") else "global"
            view = TopView(inter.author.id, mode, self.sort_by, 1)
            await view.update_embed(inter)
            return
        self.view.sort_by = self.sort_by
        self.view.page = 1
        await self.view.update_embed(inter)


class TopView(disnake.ui.View):
    def __init__(self, author_id, mode="global", sort_by="balance", page=1):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.mode = mode
        self.sort_by = sort_by
        self.page = page
        self.message = None
        
        self.add_item(TopToggleButton(mode))
        self.add_item(TopSelect(author_id, mode, sort_by))
        if author_id is None:
            self.add_item(TopPageButton("Previous", "prev", 1))
            self.add_item(TopPageButton("Next", "next", 1))
    
    async def update_embed(self, inter: disnake.MessageInteraction):
        if self.sort_by not in TOP_SORT_COLUMNS:
            self.sort_by = "balance"

        conn = get_db()
        cursor = conn.cursor()
        
        # Fetch data depending on mode
        if self.mode == "global":
            if self.sort_by == "balance":
                query = "SELECT user_id, wallet as value FROM users WHERE wallet > 0 ORDER BY wallet DESC"
            else:
                query = f"SELECT user_id, {self.sort_by} as value FROM users WHERE {self.sort_by} > 0 ORDER BY {self.sort_by} DESC"
            cursor.execute(query)
            title = "Global Leaderboard"
        else:
            guild_members = [str(member.id) for member in inter.guild.members if not member.bot]
            placeholders = ",".join(["?"] * len(guild_members))
            if guild_members:
                if self.sort_by == "balance":
                    query = f"SELECT user_id, wallet as value FROM users WHERE user_id IN ({placeholders}) AND wallet > 0 ORDER BY wallet DESC"
                else:
                    query = f"SELECT user_id, {self.sort_by} as value FROM users WHERE user_id IN ({placeholders}) AND {self.sort_by} > 0 ORDER BY {self.sort_by} DESC"
                cursor.execute(query, guild_members)
            else:
                if self.sort_by == "balance":
                    query = "SELECT user_id, wallet as value FROM users WHERE wallet > 0 ORDER BY wallet DESC"
                else:
                    query = f"SELECT user_id, {self.sort_by} as value FROM users WHERE {self.sort_by} > 0 ORDER BY {self.sort_by} DESC"
                cursor.execute(query)
            
            title = f"Server Leaderboard {inter.guild.name}"
        
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            embed = disnake.Embed(
                title=title,
                description="No users yet",
                color=EMBED_COLOR
            )
            await safe_edit(inter, embed=embed, view=TopView(inter.author.id, self.mode, self.sort_by, 1))
            return
        
        items_per_page = 10
        total_pages = (len(users) + items_per_page - 1) // items_per_page
        
        if self.page > total_pages:
            self.page = total_pages
        
        start = (self.page - 1) * items_per_page
        end = start + items_per_page
        page_users = users[start:end]
        
        leaderboard = []
        
        # Field names
        field_names = {
            "balance": "Balance",
            "total_earned": "Total earned",
            "total_spent": "Total spent",
            "work_earned": "Earned from /work",
            "collect_earned": "Earned from /collect",
            "work_count": "Jobs completed",
            "games_played": "Games played",
            "prestige_level": "Prestige"
        }
        
        field_name = field_names.get(self.sort_by, "Value")
        currency_fields = ["balance", "total_earned", "total_spent", "work_earned", "collect_earned"]
        
        for idx, (user_id, value) in enumerate(page_users, start=start + 1):
            try:
                user = await inter.bot.fetch_user(int(user_id))
                name = user.display_name if hasattr(user, 'display_name') else user.name
            except (ValueError, disnake.DiscordException):
                name = f"User {user_id}"
            
            if self.sort_by in currency_fields:
                leaderboard.append(f"**{idx}. {name}**\n{field_name}: **{value} {CURRENCY}**")
            else:
                leaderboard.append(f"**{idx}. {name}**\n{field_name}: **{value}**")
        
        embed = disnake.Embed(
            title=title,
            description=f"Sort: **{field_name}**\n\n" + "\n".join(leaderboard),
            color=EMBED_COLOR
        )
        embed.set_footer(text=f"Page {self.page}/{total_pages}")
        
        self.clear_items()
        self.add_item(TopToggleButton(self.mode))
        self.add_item(TopSelect(self.author_id, self.mode, self.sort_by))
        
        if self.page > 1:
            self.add_item(TopPageButton("Previous", "prev", self.page))
        if self.page < total_pages:
            self.add_item(TopPageButton("Next", "next", self.page))
        
        await safe_edit(inter, embed=embed, view=self)
    
class TopToggleButton(disnake.ui.Button):
    def __init__(self, mode):
        label = "Global"
        style = disnake.ButtonStyle.primary
        super().__init__(label=label, style=style, custom_id="top_toggle")
        self.mode = mode
    
    async def callback(self, inter: disnake.MessageInteraction):
        if self.view.author_id is not None and inter.author.id != self.view.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return
        await safe_defer(inter, with_message=False)
        if self.view.author_id is None:
            current = "server" if inter.message.embeds and inter.message.embeds[0].title.startswith("Server") else "global"
            view = TopView(inter.author.id, "global" if current == "server" else "server", "balance", 1)
            await view.update_embed(inter)
            return
        new_mode = "server" if self.mode == "global" else "global"
        self.view.mode = new_mode
        self.view.page = 1
        await self.view.update_embed(inter)


class TopPageButton(disnake.ui.Button):
    def __init__(self, label, direction, current_page):
        super().__init__(label=label, style=disnake.ButtonStyle.primary, custom_id=f"top_page_{direction}")
        self.direction = direction
        self.current_page = current_page
    
    async def callback(self, inter: disnake.MessageInteraction):
        if self.view.author_id is not None and inter.author.id != self.view.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return
        await safe_defer(inter, with_message=False)
        if self.view.author_id is None:
            embed = inter.message.embeds[0] if inter.message.embeds else None
            current_page = 1
            if embed and embed.footer and embed.footer.text:
                match = re.search(r"Page (\d+)/", embed.footer.text)
                if match:
                    current_page = int(match.group(1))
            mode = "server" if embed and embed.title.startswith("Server") else "global"
            reverse_names = {
                "Balance": "balance", "Total earned": "total_earned", "Total spent": "total_spent",
                "Earned from /work": "work_earned", "Earned from /collect": "collect_earned",
                "Jobs completed": "work_count", "Games played": "games_played", "Prestige": "prestige_level",
            }
            sort_by = "balance"
            if embed and embed.description:
                match = re.search(r"Sort: \*\*(.+?)\*\*", embed.description)
                if match:
                    sort_by = reverse_names.get(match.group(1), "balance")
            page = max(1, current_page - 1 if self.direction == "prev" else current_page + 1)
            view = TopView(inter.author.id, mode, sort_by, page)
            await view.update_embed(inter)
            return
        self.view.page = self.current_page - 1 if self.direction == "prev" else self.current_page + 1
        await self.view.update_embed(inter)


@bot.slash_command(name="top", description="Show leaderboard")
async def top(
    ctx: disnake.ApplicationCommandInteraction,
    page: int = commands.Param(default=1, ge=1, description="Page number")
):
    await safe_defer(ctx)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, wallet as total FROM users WHERE wallet > 0 ORDER BY wallet DESC")
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        embed = disnake.Embed(
            title="Global Leaderboard",
            description="No users yet",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed)
        return
    
    items_per_page = 10
    total_pages = (len(users) + items_per_page - 1) // items_per_page
    
    if page > total_pages:
        page = total_pages
    
    start = (page - 1) * items_per_page
    end = start + items_per_page
    page_users = users[start:end]
    
    leaderboard = []
    for idx, (user_id, total) in enumerate(page_users, start=start + 1):
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.display_name if hasattr(user, 'display_name') else user.name
        except (ValueError, disnake.DiscordException):
            name = f"User {user_id}"
        leaderboard.append(f"**{idx}. {name}**\nBalance: **{total} {CURRENCY}**")
    
    embed = disnake.Embed(
        title="Global Leaderboard",
        description="\n".join(leaderboard),
        color=EMBED_COLOR
    )
    embed.set_footer(text=f"Page {page}/{total_pages}")
    
    view = TopView(ctx.author.id, mode="global", sort_by="balance", page=page)
    view.clear_items()
    view.add_item(TopToggleButton("global"))
    view.add_item(TopSelect(ctx.author.id, "global", "balance"))
    if page > 1:
        view.add_item(TopPageButton("Previous", "prev", page))
    if page < total_pages:
        view.add_item(TopPageButton("Next", "next", page))
    
    view.message = await safe_send(ctx, embed=embed, view=view)





@bot.slash_command(name="ping", description="Show bot technical info")
async def ping(ctx: disnake.ApplicationCommandInteraction):
    ping_ms = round(bot.latency * 1000)
    
    uptime_seconds = int((datetime.now(timezone.utc) - BOT_START_TIME).total_seconds())
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    
    embed = disnake.Embed(
        title="Technical Info",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Ping",
        value=f"{ping_ms} ms",
        inline=False
    )
    embed.add_field(
        name="Started",
        value=f"<t:{int(BOT_START_TIME.timestamp())}:F>",
        inline=False
    )
    embed.set_footer(text=f"ID: {bot.user.id}")
    
    await safe_send(ctx, embed=embed)


@bot.slash_command(name="restart", description="Restart the bot (developer only)")
async def restart(ctx: disnake.ApplicationCommandInteraction):
    if ctx.author.id != DEV_ID:
        embed = disnake.Embed(
            title="Error",
            description="This command is developer-only.",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    embed = disnake.Embed(
        title="Restarting",
        description="Bot is restarting...",
        color=EMBED_COLOR
    )
    await safe_send(ctx, embed=embed, ephemeral=True)
    
    os.execv(sys.executable, [sys.executable] + sys.argv)


@bot.slash_command(name="money", description="Developer money commands")
async def money(ctx: disnake.ApplicationCommandInteraction):
    pass


@money.sub_command(name="add", description="Give cash to a user (developer only)")
async def add_money(
    ctx: disnake.ApplicationCommandInteraction,
    amount: int = commands.Param(gt=0, description="Amount"),
    user: disnake.User = commands.Param(description="User")
):
    if ctx.author.id != DEV_ID:
        embed = disnake.Embed(
            title="Error",
            description="This command is developer-only.",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    await safe_defer(ctx)
    user_data = get_user_data(user.id)
    new_wallet = user_data["wallet"] + amount
    update_user_wallet(user.id, new_wallet)
    update_stats(user.id, total_earned=amount)
    
    embed = disnake.Embed(
        title="Cash Granted",
        description=f"{ctx.author.mention} gave {user.mention} **{amount}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="New balance",
        value=f"{new_wallet} {CURRENCY}",
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await safe_send(ctx, embed=embed)


@money.sub_command(name="remove", description="Remove cash from a user (developer only)")
async def remove_money(
    ctx: disnake.ApplicationCommandInteraction,
    amount: int = commands.Param(gt=0, description="Amount"),
    user: disnake.User = commands.Param(description="User")
):
    if ctx.author.id != DEV_ID:
        embed = disnake.Embed(
            title="Error",
            description="This command is developer-only.",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    user_data = get_user_data(user.id)
    
    if user_data["wallet"] < amount:
        embed = disnake.Embed(
            title="Error",
            description=f"Not enough cash! Balance: {user_data['wallet']} {CURRENCY}",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    await safe_defer(ctx)
    new_wallet = user_data["wallet"] - amount
    update_user_wallet(user.id, new_wallet)
    
    embed = disnake.Embed(
        title="Cash Removed",
        description=f"{ctx.author.mention} removed from {user.mention} **{amount}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="New balance",
        value=f"{new_wallet} {CURRENCY}",
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await safe_send(ctx, embed=embed)


@money.sub_command(name="set", description="Set a user balance (developer only)")
async def set_money(
    ctx: disnake.ApplicationCommandInteraction,
    amount: int = commands.Param(ge=0, description="Amount (0 to reset)"),
    user: disnake.User = commands.Param(description="User")
):
    if ctx.author.id != DEV_ID:
        embed = disnake.Embed(
            title="Error",
            description="This command is developer-only.",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    await safe_defer(ctx)
    user_data = get_user_data(user.id)
    old_wallet = user_data["wallet"]
    
    update_user_wallet(user.id, amount)
    
    embed = disnake.Embed(
        title="Balance Set",
        description=f"{ctx.author.mention} set balance for {user.mention} to **{amount}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Old balance",
        value=f"{old_wallet} {CURRENCY}",
        inline=False
    )
    embed.add_field(
        name="New balance",
        value=f"{amount} {CURRENCY}",
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await safe_send(ctx, embed=embed)
