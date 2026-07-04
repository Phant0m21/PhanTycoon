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

# ==================== ПОМОЩЬ ====================

class HelpSelect(disnake.ui.Select):
    def __init__(self, author_id):
        self.author_id = author_id
        options = [
            disnake.SelectOption(label="💸 Основные", value="economy", description=""),
            disnake.SelectOption(label="🛠 Утилиты", value="utils", description=""),
            disnake.SelectOption(label="👑 Администрирование", value="admin", description="")
        ]
        super().__init__(placeholder="Выберите категорию", options=options, custom_id="help_select")
    
    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        category = inter.values[0]
        
        if category == "economy":
            embed = disnake.Embed(
                title="💸 Основные",
                description="Команды для взаимодействия с экономикой",
                color=EMBED_COLOR
            )
            embed.add_field(name="/balance", value="Показать баланс", inline=False)
            embed.add_field(name="/work", value="Заработать деньги", inline=False)
            embed.add_field(name="/deposit", value="Положить деньги в банк", inline=False)
            embed.add_field(name="/withdraw", value="Снять деньги из банка", inline=False)
            embed.add_field(name="/collect", value="Собрать доход с бизнесов", inline=False)
            embed.add_field(name="/top", value="Показать топ игроков", inline=False)
            embed.add_field(name="/shop", value="Открыть магазин", inline=False)
            embed.add_field(name="/buy", value="Купить товар", inline=False)
            embed.add_field(name="/inventory", value="Показать инвентарь", inline=False)
            embed.add_field(name="/profile", value="Показать профиль", inline=False)
            embed.add_field(name="/coinflip", value="Подбросить монетку", inline=False)
            embed.add_field(name="/mine", value="Пойти в шахту", inline=False)
            embed.add_field(name="/shop_upgrades", value="Улучшения", inline=False)
            
        elif category == "utils":
            embed = disnake.Embed(
                title="🛠 Утилиты",
                description="Полезные команды",
                color=EMBED_COLOR
            )
            embed.add_field(name="/ping", value="Показать техническую информацию", inline=False)
            
        elif category == "admin":
            embed = disnake.Embed(
                title="👑 Администрирование",
                description="Команды для администрации",
                color=EMBED_COLOR
            )
            embed.add_field(name="/add_money", value="Выдать деньги пользователю", inline=False)
            embed.add_field(name="/remove_money", value="Забрать деньги у пользователя", inline=False)
            embed.add_field(name="/set_money", value="Установить точную сумму", inline=False)
            embed.add_field(name="/restart", value="Перезапустить бота (только для разработчика)", inline=False)
        
        await inter.response.edit_message(embed=embed, view=self.view)


class HelpView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(author_id))


@bot.slash_command(name="help", description="Показать список команд")
async def help(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="Помощь по боту",
        description="Выберите категорию в меню ниже, чтобы увидеть команды",
        color=EMBED_COLOR
    )
    view = HelpView(ctx.author.id)
    await ctx.response.defer()
    await ctx.followup.send(embed=embed, view=view)
