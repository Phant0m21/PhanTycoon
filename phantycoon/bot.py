import asyncio
import sys

import disnake
from disnake.ext import commands

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.InteractionBot(
    intents=intents,
    # Every global command is available both to server-installed and
    # user-installed copies of the app. Subcommands inherit these defaults.
    default_install_types=disnake.ApplicationInstallTypes.all(),
    default_contexts=disnake.InteractionContextTypes.all(),
)
