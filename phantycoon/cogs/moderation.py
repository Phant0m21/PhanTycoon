from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import DEV_ID, EMBED_COLOR
from phantycoon.database import (
    clear_all_captcha_state, create_bot_ban, get_bot_ban,
    get_captcha_status, is_captcha_banned, list_active_bans, remove_bot_ban,
)
from phantycoon.interactions import safe_embed, safe_send


BAN_REASONS = {
    "Automation / macros": "Automation / macros",
    "Exploiting bugs": "Exploiting bugs",
    "Scamming": "Scamming",
    "Abuse or harassment": "Abuse or harassment",
    "Alt-account abuse": "Alt-account abuse",
    "Suspicious activity": "Suspicious activity",
    "Other": "Other",
}

DURATION_UNITS = {
    "Minutes": "minutes",
    "Hours": "hours",
    "Days": "days",
    "Weeks": "weeks",
    "Permanent": "permanent",
}

UNBAN_REASONS = {
    "Appeal accepted": "Appeal accepted",
    "Ban expired / served": "Ban expired / served",
    "Incorrect ban": "Incorrect ban",
    "Captcha ban cleared": "Captcha ban cleared",
    "Evidence reviewed": "Evidence reviewed",
    "Other": "Other",
}


def is_owner(inter):
    return inter.author.id == DEV_ID


def build_reason(reason, details):
    details = (details or "").strip()
    return f"{reason}: {details}" if details else reason


def get_expiration(amount, unit):
    if unit == "permanent":
        return None
    return datetime.now(timezone.utc) + timedelta(**{unit: amount})


@bot.slash_command(name="ban", description="Bot ban management")
async def ban(ctx: disnake.ApplicationCommandInteraction):
    pass


@ban.sub_command(name="add", description="Ban a user from using the bot")
async def ban_user(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="User to ban"),
    reason: str = commands.Param(choices=BAN_REASONS, description="Ban reason"),
    duration: int = commands.Param(default=1, ge=1, le=10000, description="Duration amount"),
    unit: str = commands.Param(default="days", choices=DURATION_UNITS, description="Duration unit"),
    details: str = commands.Param(default=None, max_length=300, description="Additional details"),
    notify: bool = commands.Param(default=True, description="Notify the user by DM"),
):
    if not is_owner(ctx):
        await safe_embed(ctx, "Access denied", "Only the bot owner can use this command.", ephemeral=True)
        return
    if user.id == DEV_ID:
        await safe_embed(ctx, "Error", "The bot owner cannot be banned.", ephemeral=True)
        return
    if user.bot:
        await safe_embed(ctx, "Error", "Bot accounts cannot be banned from the economy bot.", ephemeral=True)
        return

    full_reason = build_reason(reason, details)
    expires_at = get_expiration(duration, unit)
    create_bot_ban(user.id, ctx.author.id, full_reason, expires_at)
    if expires_at:
        time_text = f"until <t:{int(expires_at.timestamp())}:F> (<t:{int(expires_at.timestamp())}:R>)"
    else:
        time_text = "permanently"

    dm_delivered = False
    if notify:
        embed = disnake.Embed(
            title="You have been banned from PhanTycoon",
            description=f"**Reason:** {full_reason}\n**Duration:** {time_text}",
            color=EMBED_COLOR,
        )
        try:
            await user.send(embed=embed)
            dm_delivered = True
        except disnake.DiscordException:
            pass

    notify_text = "DM delivered" if dm_delivered else ("DM could not be delivered" if notify else "DM disabled")
    await safe_embed(ctx, "User banned", f"{user.mention} was banned {time_text}.\n**Reason:** {full_reason}\n**Notification:** {notify_text}", ephemeral=True)


@ban.sub_command(name="list", description="Show all active bot and captcha bans")
async def ban_list(
    ctx: disnake.ApplicationCommandInteraction,
    page: int = commands.Param(default=1, ge=1, description="Page number"),
):
    if not is_owner(ctx):
        await safe_embed(ctx, "Access denied", "Only bot developers can use this command.", ephemeral=True)
        return
    bans = list_active_bans()
    if not bans:
        await safe_embed(ctx, "Active bans", "There are no active bans.", ephemeral=True)
        return
    per_page = 10
    total_pages = (len(bans) + per_page - 1) // per_page
    page = min(page, total_pages)
    lines = []
    for index, entry in enumerate(bans[(page - 1) * per_page:page * per_page], start=(page - 1) * per_page + 1):
        until = "Permanent" if entry["is_permanent"] else f"<t:{int(datetime.fromisoformat(entry['expires_at']).timestamp())}:R>"
        source = "Captcha" if entry["source"] == "captcha" else "Moderation"
        moderator = f" • by <@{entry['moderator_id']}>" if entry["moderator_id"] else ""
        lines.append(f"**{index}.** <@{entry['user_id']}> (`{entry['user_id']}`)\n{source} • {until}{moderator}\nReason: {entry['reason']}")
    embed = disnake.Embed(title=f"Active bans — {len(bans)}", description="\n\n".join(lines), color=EMBED_COLOR)
    embed.set_footer(text=f"Page {page}/{total_pages}")
    await safe_send(ctx, embed=embed, ephemeral=True)


@bot.slash_command(name="unban", description="Remove bot and captcha bans from a user")
async def unban_user(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="User to unban"),
    reason: str = commands.Param(default="Appeal accepted", choices=UNBAN_REASONS, description="Unban reason"),
    details: str = commands.Param(default=None, max_length=300, description="Additional details"),
    clear_captcha: bool = commands.Param(default=True, description="Also clear captcha ban and challenge"),
    notify: bool = commands.Param(default=True, description="Notify the user by DM"),
):
    if not is_owner(ctx):
        await safe_embed(ctx, "Access denied", "Only the bot owner can use this command.", ephemeral=True)
        return

    full_reason = build_reason(reason, details)
    bot_ban = get_bot_ban(user.id)
    captcha_status = get_captcha_status(user.id)
    captcha_banned, _ = is_captcha_banned(captcha_status)
    captcha_active = bool(captcha_status and captcha_status["is_captcha_active"])
    removed_bot_ban = remove_bot_ban(user.id)
    removed_captcha = False
    if clear_captcha and (captcha_banned or captcha_active):
        clear_all_captcha_state(user.id)
        removed_captcha = True

    if not removed_bot_ban and not removed_captcha:
        await safe_embed(ctx, "Nothing to remove", f"{user.mention} has no active matching ban.", ephemeral=True)
        return

    removed = []
    if removed_bot_ban or bot_ban:
        removed.append("bot ban")
    if removed_captcha:
        removed.append("captcha ban/challenge")

    dm_delivered = False
    if notify:
        embed = disnake.Embed(
            title="You have been unbanned from PhanTycoon",
            description=f"**Reason:** {full_reason}\nYou can use the bot again.",
            color=EMBED_COLOR,
        )
        try:
            await user.send(embed=embed)
            dm_delivered = True
        except disnake.DiscordException:
            pass

    notify_text = "DM delivered" if dm_delivered else ("DM could not be delivered" if notify else "DM disabled")
    await safe_embed(ctx, "User unbanned", f"Removed: **{', '.join(removed)}**.\n**Reason:** {full_reason}\n**Notification:** {notify_text}", ephemeral=True)


@bot.slash_command_check
async def bot_ban_check(ctx: disnake.ApplicationCommandInteraction):
    if ctx.author.id == DEV_ID:
        return True
    ban = get_bot_ban(ctx.author.id)
    if not ban:
        return True
    if ban["is_permanent"]:
        duration = "This ban is permanent."
    else:
        expires_at = datetime.fromisoformat(ban["expires_at"])
        duration = f"Expires <t:{int(expires_at.timestamp())}:R>."
    await safe_embed(ctx, "Bot access suspended", f"**Reason:** {ban['reason']}\n{duration}", ephemeral=True)
    return False
