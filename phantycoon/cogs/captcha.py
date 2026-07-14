import random
import string
from io import BytesIO

import disnake
from disnake.ext import commands
from PIL import Image, ImageDraw, ImageFont

from phantycoon.bot import bot
from phantycoon.config import EMBED_COLOR
from phantycoon.database import (
    CAPTCHA_BAN_DAYS,
    CAPTCHA_MAX_ATTEMPTS,
    CAPTCHA_MAX_REGENS,
    activate_captcha,
    ban_for_failed_captcha,
    clear_captcha,
    get_captcha_status,
    increment_captcha_attempts,
    is_captcha_banned,
    regenerate_captcha,
)
from phantycoon.interactions import safe_send

CAPTCHA_BLOCK_MESSAGE = "You cannot use any commands. Please solve the active captcha first using /verify [code]!"


def generate_captcha_code():
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(4))


def create_captcha_file(code):
    image = Image.new("RGB", (320, 140), (247, 249, 252))
    draw = ImageDraw.Draw(image)

    for _ in range(18):
        x1 = random.randint(0, 320)
        y1 = random.randint(0, 140)
        x2 = random.randint(0, 320)
        y2 = random.randint(0, 140)
        color = (
            random.randint(120, 210),
            random.randint(120, 210),
            random.randint(120, 210),
        )
        draw.line((x1, y1, x2, y2), fill=color, width=random.randint(1, 3))

    try:
        font = ImageFont.truetype("arial.ttf", 56)
    except OSError:
        font = ImageFont.load_default()

    for index, char in enumerate(code):
        x = 50 + index * 55 + random.randint(-5, 5)
        y = 38 + random.randint(-8, 8)
        color = (
            random.randint(20, 80),
            random.randint(30, 90),
            random.randint(50, 120),
        )
        draw.text((x, y), char, font=font, fill=color)

    for _ in range(90):
        x = random.randint(0, 319)
        y = random.randint(0, 139)
        draw.point((x, y), fill=(random.randint(60, 180), random.randint(60, 180), random.randint(60, 180)))

    buffer = BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)
    return disnake.File(buffer, filename="captcha.png")


async def send_captcha(inter, code, *, title="Captcha Required"):
    embed = disnake.Embed(
        title=title,
        description="Enter the case-sensitive code from the image using `/verify [code]`.",
        color=EMBED_COLOR,
    )
    embed.set_image(url="attachment://captcha.png")
    await safe_send(inter, embed=embed, file=create_captcha_file(code), ephemeral=True)


async def send_failed_captcha_ban(inter, banned_until):
    description = (
        f"You failed the active captcha {CAPTCHA_MAX_ATTEMPTS} times.\n"
        f"You are banned from using the bot for {CAPTCHA_BAN_DAYS} days.\n"
        f"Reason: failed Visual Anti-Bot Captcha.\n"
        f"Banned until: <t:{int(banned_until.timestamp())}:F>"
    )
    embed = disnake.Embed(title="Captcha Failed", description=description, color=EMBED_COLOR)

    try:
        await inter.author.send(embed=embed)
        await safe_send(inter, "Captcha failed. I sent the ban details to your DMs.", ephemeral=True)
    except disnake.HTTPException:
        await safe_send(inter, embed=embed)


async def block_if_captcha_active(inter):
    status = get_captcha_status(inter.author.id)
    banned, banned_until = is_captcha_banned(status)
    if banned:
        await safe_send(
            inter,
            f"You are banned from using the bot until <t:{int(banned_until.timestamp())}:F>.",
            ephemeral=True,
        )
        return True

    if status and status["is_captcha_active"]:
        await safe_send(inter, CAPTCHA_BLOCK_MESSAGE, ephemeral=True)
        return True

    return False


@bot.slash_command_check
async def captcha_command_check(ctx: disnake.ApplicationCommandInteraction):
    command = getattr(ctx.application_command, "qualified_name", "")
    root_command = command.split(" ", 1)[0]
    if root_command in {"verify", "verify_regen"}:
        return True

    if await block_if_captcha_active(ctx):
        return False
    return True


@bot.slash_command(name="verify", description="Solve your active captcha")
async def verify(ctx: disnake.ApplicationCommandInteraction, code: str):
    status = get_captcha_status(ctx.author.id)
    banned, banned_until = is_captcha_banned(status)
    if banned:
        await safe_send(
            ctx,
            f"You are banned from using the bot until <t:{int(banned_until.timestamp())}:F>.",
            ephemeral=True,
        )
        return

    if not status or not status["is_captcha_active"] or not status["captcha_code"]:
        await safe_send(ctx, "You do not have an active captcha.", ephemeral=True)
        return

    if code == status["captcha_code"]:
        clear_captcha(ctx.author.id)
        await safe_send(ctx, "Captcha solved. You can use bot commands again.", ephemeral=True)
        return

    attempts = increment_captcha_attempts(ctx.author.id)
    remaining = CAPTCHA_MAX_ATTEMPTS - attempts
    if remaining <= 0:
        banned_until = ban_for_failed_captcha(ctx.author.id)
        await send_failed_captcha_ban(ctx, banned_until)
        return

    await safe_send(
        ctx,
        f"Wrong captcha code. Attempts left: **{remaining}**.",
        ephemeral=True,
    )


@bot.slash_command(name="verify_regen", description="Regenerate your active captcha")
async def verify_regen(ctx: disnake.ApplicationCommandInteraction):
    status = get_captcha_status(ctx.author.id)
    banned, banned_until = is_captcha_banned(status)
    if banned:
        await safe_send(
            ctx,
            f"You are banned from using the bot until <t:{int(banned_until.timestamp())}:F>.",
            ephemeral=True,
        )
        return

    if not status or not status["is_captcha_active"]:
        await safe_send(ctx, "You do not have an active captcha.", ephemeral=True)
        return

    if status["captcha_regens"] >= CAPTCHA_MAX_REGENS:
        await safe_send(ctx, "You have no captcha regenerations left.", ephemeral=True)
        return

    code = generate_captcha_code()
    regenerate_captcha(ctx.author.id, code)
    await send_captcha(ctx, code, title="Captcha Regenerated")


def setup_captcha_for_user(user_id):
    code = generate_captcha_code()
    activate_captcha(user_id, code)
    return code
