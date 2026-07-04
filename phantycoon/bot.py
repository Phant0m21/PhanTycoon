import asyncio
import sys

import disnake
from disnake.ext import commands

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.InteractionBot(intents=intents)
