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

TOP_SORT_COLUMNS = {
    "balance",
    "total_earned",
    "total_spent",
    "work_earned",
    "collect_earned",
    "work_count",
    "games_played",
}

# ==================== ТОП С ПЕРЕКЛЮЧЕНИЕМ И СОРТИРОВКОЙ ====================

class TopSelect(disnake.ui.Select):
    def __init__(self, author_id, mode="global", sort_by="balance"):
        self.author_id = author_id
        self.mode = mode
        self.sort_by = sort_by
        
        options = [
            disnake.SelectOption(
                label="💰 Общий баланс",
                value="balance",
                description="Текущий баланс",
                emoji="💰"
            ),
            disnake.SelectOption(
                label="💵 Всего заработано",
                value="total_earned",
                description="Всего заработано за всё время",
                emoji="💵"
            ),
            disnake.SelectOption(
                label="💸 Всего потрачено",
                value="total_spent",
                description="Всего потрачено за всё время",
                emoji="💸"
            ),
            disnake.SelectOption(
                label="🛠 Заработано с работ",
                value="work_earned",
                description="Заработано через работу",
                emoji="🛠"
            ),
            disnake.SelectOption(
                label="🏢 Заработано с бизнесов",
                value="collect_earned",
                description="Заработано с бизнесов",
                emoji="🏢"
            ),
            disnake.SelectOption(
                label="📊 Выполнено работ",
                value="work_count",
                description="Количество выполненных работ",
                emoji="📊"
            ),
            disnake.SelectOption(
                label="🎮 Сыграно мини-игр",
                value="games_played",
                description="Количество сыгранных мини-игр",
                emoji="🎮"
            )
        ]
        super().__init__(
            placeholder="Выберите сортировку",
            options=options,
            custom_id="top_sort_select"
        )
    
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.author_id:
            await safe_send(inter, "❌ Это не ваше меню!", ephemeral=True)
            return
        
        await safe_defer(inter, with_message=False)
        self.sort_by = inter.values[0]
        self.view.sort_by = self.sort_by
        self.view.page = 1
        await self.view.update_embed(inter)


class TopView(disnake.ui.View):
    def __init__(self, author_id, mode="global", sort_by="balance", page=1):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.mode = mode
        self.sort_by = sort_by
        self.page = page
        self.message = None
        
        self.add_item(TopToggleButton(mode))
        self.add_item(TopSelect(author_id, mode, sort_by))
    
    async def update_embed(self, inter: disnake.MessageInteraction):
        if self.sort_by not in TOP_SORT_COLUMNS:
            self.sort_by = "balance"

        conn = get_db()
        cursor = conn.cursor()
        
        # Получаем данные в зависимости от режима
        if self.mode == "global":
            if self.sort_by == "balance":
                query = "SELECT user_id, wallet + bank as value FROM users WHERE wallet + bank > 0 ORDER BY value DESC"
            else:
                query = f"SELECT user_id, {self.sort_by} as value FROM users WHERE {self.sort_by} > 0 ORDER BY {self.sort_by} DESC"
            cursor.execute(query)
            title = "Глобальный лидерборд"
        else:
            guild_members = [str(member.id) for member in inter.guild.members if not member.bot]
            placeholders = ",".join(["?"] * len(guild_members))
            if guild_members:
                if self.sort_by == "balance":
                    query = f"SELECT user_id, wallet + bank as value FROM users WHERE user_id IN ({placeholders}) AND wallet + bank > 0 ORDER BY value DESC"
                else:
                    query = f"SELECT user_id, {self.sort_by} as value FROM users WHERE user_id IN ({placeholders}) AND {self.sort_by} > 0 ORDER BY {self.sort_by} DESC"
                cursor.execute(query, guild_members)
            else:
                if self.sort_by == "balance":
                    query = "SELECT user_id, wallet + bank as value FROM users WHERE wallet + bank > 0 ORDER BY value DESC"
                else:
                    query = f"SELECT user_id, {self.sort_by} as value FROM users WHERE {self.sort_by} > 0 ORDER BY {self.sort_by} DESC"
                cursor.execute(query)
            
            title = f"Лидерборд сервера {inter.guild.name}"
        
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            embed = disnake.Embed(
                title=title,
                description="Нет пользователей",
                color=EMBED_COLOR
            )
            await safe_edit(inter, embed=embed, view=self)
            return
        
        items_per_page = 10
        total_pages = (len(users) + items_per_page - 1) // items_per_page
        
        if self.page > total_pages:
            self.page = total_pages
        
        start = (self.page - 1) * items_per_page
        end = start + items_per_page
        page_users = users[start:end]
        
        admin = await inter.bot.fetch_user(DEV_ID)
        leaderboard = []
        
        # Названия для полей
        field_names = {
            "balance": "Общий баланс",
            "total_earned": "Всего заработано",
            "total_spent": "Всего потрачено",
            "work_earned": "Заработано с /work",
            "collect_earned": "Заработано с /collect",
            "work_count": "Выполнено работ",
            "games_played": "Сыграно игр"
        }
        
        field_name = field_names.get(self.sort_by, "Значение")
        currency_fields = ["balance", "total_earned", "total_spent", "work_earned", "collect_earned"]
        
        for idx, (user_id, value) in enumerate(page_users, start=start + 1):
            try:
                user = await inter.bot.fetch_user(int(user_id))
                name = user.display_name if hasattr(user, 'display_name') else user.name
            except (ValueError, disnake.DiscordException):
                name = f"Пользователь {user_id}"
            
            if self.sort_by in currency_fields:
                leaderboard.append(f"{idx}. {name} • {value} {CURRENCY}")
            else:
                leaderboard.append(f"{idx}. {name} • {value}")
        
        embed = disnake.Embed(
            title=title,
            description=f"Админ бота: {admin.mention}\nСортировка: **{field_name}**\n\n" + "\n".join(leaderboard),
            color=EMBED_COLOR
        )
        embed.set_footer(text=f"Страница {self.page}/{total_pages}")
        
        self.clear_items()
        self.add_item(TopToggleButton(self.mode))
        self.add_item(TopSelect(self.author_id, self.mode, self.sort_by))
        
        if self.page > 1:
            self.add_item(TopPageButton("◀", "prev", self.page))
        if self.page < total_pages:
            self.add_item(TopPageButton("▶", "next", self.page))
        
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


class TopToggleButton(disnake.ui.Button):
    def __init__(self, mode):
        label = "Global"
        style = disnake.ButtonStyle.primary if mode == "global" else disnake.ButtonStyle.secondary
        super().__init__(label=label, style=style, custom_id="top_toggle")
        self.mode = mode
    
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author_id:
            await safe_send(inter, "❌ Это не ваше меню!", ephemeral=True)
            return
        await safe_defer(inter, with_message=False)
        new_mode = "server" if self.mode == "global" else "global"
        self.view.mode = new_mode
        self.view.page = 1
        await self.view.update_embed(inter)


class TopPageButton(disnake.ui.Button):
    def __init__(self, label, direction, current_page):
        super().__init__(label=label, style=disnake.ButtonStyle.secondary, custom_id=f"top_page_{direction}")
        self.direction = direction
        self.current_page = current_page
    
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author_id:
            await safe_send(inter, "❌ Это не ваше меню!", ephemeral=True)
            return
        await safe_defer(inter, with_message=False)
        self.view.page = self.current_page - 1 if self.direction == "prev" else self.current_page + 1
        await self.view.update_embed(inter)


@bot.slash_command(name="top", description="Показать топ участников")
async def top(
    ctx: disnake.ApplicationCommandInteraction,
    page: int = commands.Param(default=1, ge=1, description="Номер страницы")
):
    await safe_defer(ctx)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, wallet + bank as total FROM users WHERE wallet + bank > 0 ORDER BY total DESC")
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        embed = disnake.Embed(
            title="Глобальный лидерборд",
            description="Нет пользователей",
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
    
    admin = await bot.fetch_user(DEV_ID)
    leaderboard = []
    for idx, (user_id, total) in enumerate(page_users, start=start + 1):
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.display_name if hasattr(user, 'display_name') else user.name
        except (ValueError, disnake.DiscordException):
            name = f"Пользователь {user_id}"
        leaderboard.append(f"{idx}. {name} • {total} {CURRENCY}")
    
    embed = disnake.Embed(
        title="Глобальный лидерборд",
        description=f"Админ бота: {admin.mention}\n\n" + "\n".join(leaderboard),
        color=EMBED_COLOR
    )
    embed.set_footer(text=f"Страница {page}/{total_pages}")
    
    view = TopView(ctx.author.id, mode="global", sort_by="balance", page=page)
    view.clear_items()
    view.add_item(TopToggleButton("global"))
    view.add_item(TopSelect(ctx.author.id, "global", "balance"))
    if page > 1:
        view.add_item(TopPageButton("◀", "prev", page))
    if page < total_pages:
        view.add_item(TopPageButton("▶", "next", page))
    
    view.message = await safe_send(ctx, embed=embed, view=view)





@bot.slash_command(name="ping", description="Показать техническую информацию бота")
async def ping(ctx: disnake.ApplicationCommandInteraction):
    ping_ms = round(bot.latency * 1000)
    
    uptime_seconds = int((datetime.now(timezone.utc) - BOT_START_TIME).total_seconds())
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    uptime_str = f"{days}д {hours}ч {minutes}м {seconds}с"
    
    embed = disnake.Embed(
        title="Техническая информация",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Пинг",
        value=f"{ping_ms} мс",
        inline=False
    )
    embed.add_field(
        name="Запущен",
        value=f"<t:{int(BOT_START_TIME.timestamp())}:F>",
        inline=False
    )
    embed.set_footer(text=f"ID: {bot.user.id}")
    
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed)


@bot.slash_command(name="restart", description="Перезапустить бота (только для разработчика)")
async def restart(ctx: disnake.ApplicationCommandInteraction):
    if ctx.author.id != DEV_ID:
        embed = disnake.Embed(
            title="Ошибка",
            description="Эта команда доступна только разработчику бота!",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    embed = disnake.Embed(
        title="Перезагрузка",
        description="Бот перезапускается...",
        color=EMBED_COLOR
    )
    await safe_send(ctx, embed=embed, ephemeral=True)
    
    os.execv(sys.executable, [sys.executable] + sys.argv)


@bot.slash_command(name="add_money", description="Выдать деньги пользователю (только для разработчика)")
async def add_money(
    ctx: disnake.ApplicationCommandInteraction,
    amount: int = commands.Param(gt=0, description="Сумма"),
    user: disnake.User = commands.Param(description="Пользователь")
):
    if ctx.author.id != DEV_ID:
        embed = disnake.Embed(
            title="Ошибка",
            description="Эта команда доступна только разработчику бота!",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    user_data = get_user_data(user.id)
    new_wallet = user_data["wallet"] + amount
    update_user_wallet(user.id, new_wallet)
    update_stats(user.id, total_earned=amount)
    
    embed = disnake.Embed(
        title="Выдача денег",
        description=f"{ctx.author.mention} выдал {user.mention} **{amount}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Новый баланс",
        value=f"{new_wallet} {CURRENCY}",
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed)


@bot.slash_command(name="remove_money", description="Забрать деньги у пользователя (только для разработчика)")
async def remove_money(
    ctx: disnake.ApplicationCommandInteraction,
    amount: int = commands.Param(gt=0, description="Сумма"),
    user: disnake.User = commands.Param(description="Пользователь")
):
    if ctx.author.id != DEV_ID:
        embed = disnake.Embed(
            title="Ошибка",
            description="Эта команда доступна только разработчику бота!",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    user_data = get_user_data(user.id)
    
    if user_data["wallet"] < amount:
        embed = disnake.Embed(
            title="Ошибка",
            description=f"Недостаточно денег! Баланс: {user_data['wallet']} {CURRENCY}",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    new_wallet = user_data["wallet"] - amount
    update_user_wallet(user.id, new_wallet)
    
    embed = disnake.Embed(
        title="Списание денег",
        description=f"{ctx.author.mention} забрал у {user.mention} **{amount}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Новый баланс",
        value=f"{new_wallet} {CURRENCY}",
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed)


@bot.slash_command(name="set_money", description="Установить точную сумму денег пользователю (только для разработчика)")
async def set_money(
    ctx: disnake.ApplicationCommandInteraction,
    amount: int = commands.Param(ge=0, description="Сумма (0 - обнулить)"),
    user: disnake.User = commands.Param(description="Пользователь")
):
    if ctx.author.id != DEV_ID:
        embed = disnake.Embed(
            title="Ошибка",
            description="Эта команда доступна только разработчику бота!",
            color=EMBED_COLOR
        )
        await safe_send(ctx, embed=embed, ephemeral=True)
        return
    
    user_data = get_user_data(user.id)
    old_wallet = user_data["wallet"]
    
    update_user_wallet(user.id, amount)
    
    embed = disnake.Embed(
        title="Установка баланса",
        description=f"{ctx.author.mention} установил баланс {user.mention} на **{amount}** {CURRENCY}",
        color=EMBED_COLOR
    )
    embed.add_field(
        name="Старый баланс",
        value=f"{old_wallet} {CURRENCY}",
        inline=True
    )
    embed.add_field(
        name="Новый баланс",
        value=f"{amount} {CURRENCY}",
        inline=True
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed)
