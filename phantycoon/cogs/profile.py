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

# ==================== ПРОФИЛЬ ====================

class ProfileView(disnake.ui.View):
    def __init__(self, author_id, target_id, mode="profile"):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.target_id = target_id
        self.mode = mode
        self.message = None
        
        self.add_item(ProfileButton("Профиль", "profile", disnake.ButtonStyle.primary if mode == "profile" else disnake.ButtonStyle.secondary))
        self.add_item(ProfileButton("Статистика", "stats", disnake.ButtonStyle.primary if mode == "stats" else disnake.ButtonStyle.secondary))
    
    async def update_embed(self, inter: disnake.MessageInteraction):
        target = await inter.bot.fetch_user(self.target_id)
        user_data = get_user_data(self.target_id)
        
        if self.mode == "profile":
            embed = disnake.Embed(
                title=f"Профиль {target.name}",
                color=EMBED_COLOR
            )
            
            total = user_data["wallet"] + user_data["bank"]
            
            embed.add_field(
                name="Престиж",
                value="0",
                inline=False
            )
            embed.add_field(
                name="Клан",
                value="Не в клане",
                inline=False
            )
            embed.add_field(
                name="Общий баланс",
                value=f"{total} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Кошелёк",
                value=f"{user_data['wallet']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Банк",
                value=f"{user_data['bank']} {CURRENCY}",
                inline=False
            )
            
            # Текущая кирка
            current_pickaxe = user_data.get("current_pickaxe", "Каменная кирка")
            pickaxe_emoji = PICKAXES.get(current_pickaxe, {}).get("emoji", "")
            embed.add_field(
                name="Кирка",
                value=f"{pickaxe_emoji} {current_pickaxe}",
                inline=False
            )
            
            # Уровни апгрейдов
            time_level = user_data.get("time_management_level", 0)
            business_level = user_data.get("business_optimization_level", 0)
            miner_level = user_data.get("miner_boost_level", 0)
            
            embed.add_field(
                name="⏱️ Менеджмент времени",
                value=f"Уровень {time_level}/{UPGRADES['time_management']['max_level']}",
                inline=True
            )
            embed.add_field(
                name="🏢 Оптимизация бизнесов",
                value=f"Уровень {business_level}/{UPGRADES['business_optimization']['max_level']}",
                inline=True
            )
            embed.add_field(
                name="⛏️ Майнер руды",
                value=f"Уровень {miner_level}/{UPGRADES['miner_boost']['max_level']}",
                inline=True
            )
            
            businesses = get_user_businesses(self.target_id)
            if businesses:
                embed.add_field(
                    name="Активные бизнесы",
                    value="\n".join(businesses),
                    inline=False
                )
            else:
                embed.add_field(
                    name="Активные бизнесы",
                    value="Нет",
                    inline=False
                )
            
            embed.set_thumbnail(url=target.display_avatar.url)
            
        else:  # stats
            embed = disnake.Embed(
                title=f"Статистика {target.name}",
                color=EMBED_COLOR
            )
            
            registered_dt = datetime.fromisoformat(user_data["registered_at"])
            months = {
                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
            }
            registered = f"{registered_dt.day} {months[registered_dt.month]} {registered_dt.year}"
            
            embed.add_field(
                name="Дата регистрации",
                value=registered,
                inline=False
            )
            embed.add_field(
                name="Всего заработано за всё время",
                value=f"{user_data['total_earned']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Всего потрачено за всё время",
                value=f"{user_data['total_spent']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Заработано с /work",
                value=f"{user_data['work_earned']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Заработано с /collect",
                value=f"{user_data['collect_earned']} {CURRENCY}",
                inline=False
            )
            embed.add_field(
                name="Выполнено работ",
                value=f"{user_data['work_count']}",
                inline=False
            )
            embed.add_field(
                name="Сыграно мини-игр",
                value=f"{user_data['games_played']}",
                inline=False
            )
            
            embed.set_thumbnail(url=target.display_avatar.url)
        
        self.clear_items()
        self.add_item(ProfileButton("Профиль", "profile", disnake.ButtonStyle.primary if self.mode == "profile" else disnake.ButtonStyle.secondary))
        self.add_item(ProfileButton("Статистика", "stats", disnake.ButtonStyle.primary if self.mode == "stats" else disnake.ButtonStyle.secondary))
        
        await inter.response.edit_message(embed=embed, view=self)
    
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
            await inter.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        self.view.mode = self.mode
        await self.view.update_embed(inter)


@bot.slash_command(name="profile", description="Показать профиль пользователя")
async def profile(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(default=None, description="Пользователь")
):
    target = user or ctx.author
    user_data = get_user_data(target.id)
    
    embed = disnake.Embed(
        title=f"Профиль {target.name}",
        color=EMBED_COLOR
    )
    
    total = user_data["wallet"] + user_data["bank"]
    
    embed.add_field(
        name="Престиж",
        value="0",
        inline=False
    )
    embed.add_field(
        name="Клан",
        value="Не в клане",
        inline=False
    )
    embed.add_field(
        name="Общий баланс",
        value=f"{total} {CURRENCY}",
        inline=False
    )
    embed.add_field(
        name="Кошелёк",
        value=f"{user_data['wallet']} {CURRENCY}",
        inline=False
    )
    embed.add_field(
        name="Банк",
        value=f"{user_data['bank']} {CURRENCY}",
        inline=False
    )
    
    # Текущая кирка
    current_pickaxe = user_data.get("current_pickaxe", "Каменная кирка")
    pickaxe_emoji = PICKAXES.get(current_pickaxe, {}).get("emoji", "")
    embed.add_field(
        name="Кирка",
        value=f"{pickaxe_emoji} {current_pickaxe}",
        inline=False
    )
    
    # Уровни апгрейдов
    time_level = user_data.get("time_management_level", 0)
    business_level = user_data.get("business_optimization_level", 0)
    miner_level = user_data.get("miner_boost_level", 0)
    
    embed.add_field(
        name="⏱️ Менеджмент времени",
        value=f"Уровень {time_level}/{UPGRADES['time_management']['max_level']}",
        inline=True
    )
    embed.add_field(
        name="🏢 Оптимизация бизнесов",
        value=f"Уровень {business_level}/{UPGRADES['business_optimization']['max_level']}",
        inline=True
    )
    embed.add_field(
        name="⛏️ Майнер руды",
        value=f"Уровень {miner_level}/{UPGRADES['miner_boost']['max_level']}",
        inline=True
    )
    
    businesses = get_user_businesses(target.id)
    if businesses:
        embed.add_field(
            name="Активные бизнесы",
            value="\n".join(businesses),
            inline=False
        )
    else:
        embed.add_field(
            name="Активные бизнесы",
            value="Нет",
            inline=False
        )
    
    embed.set_thumbnail(url=target.display_avatar.url)
    
    view = ProfileView(ctx.author.id, target.id, mode="profile")
    
    await ctx.response.defer()
    view.message = await ctx.followup.send(embed=embed, view=view)
