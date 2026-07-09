from datetime import datetime, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import CURRENCY, EMBED_COLOR
from phantycoon.database import *
from phantycoon.interactions import safe_send


def format_clan_bonus(level):
    return f"{level * 0.5:.1f}%"


@bot.slash_command(name="clan", description="Clan commands")
async def clan(ctx: disnake.ApplicationCommandInteraction):
    pass


@clan.sub_command(name="create", description="Create a clan")
async def clan_create(
    ctx: disnake.ApplicationCommandInteraction,
    name: str = commands.Param(description="Clan name", min_length=3, max_length=32),
    tag: str = commands.Param(description="Clan tag", min_length=2, max_length=6),
):
    success, status, clan_data = create_clan(ctx.author.id, name.strip(), tag.strip().upper())
    if not success:
        messages = {
            "already_in_clan": "You are already in a clan.",
            "name_taken": "A clan with this name already exists.",
            "cash": f"You need **{CLAN_CREATE_COST:,} {CURRENCY}** to create a clan.",
        }
        await safe_send(ctx, f"❌ {messages.get(status, 'Could not create clan.')}", ephemeral=True)
        return

    embed = disnake.Embed(
        title=f"[{clan_data['tag']}] {clan_data['name']}",
        description=f"{ctx.author.mention} created a clan and became **Leader**.",
        color=EMBED_COLOR,
    )
    embed.add_field(name="Cost", value=f"{CLAN_CREATE_COST:,} {CURRENCY}", inline=True)
    embed.add_field(name="Access", value="Public", inline=True)
    embed.add_field(name="Mining Efficiency", value=format_clan_bonus(clan_data["level"]), inline=True)
    await safe_send(ctx, embed=embed)


@clan.sub_command(name="join", description="Join a clan")
async def clan_join(
    ctx: disnake.ApplicationCommandInteraction,
    name: str = commands.Param(description="Clan name"),
):
    success, status, clan_data = join_clan(ctx.author.id, name.strip())
    if not success:
        messages = {
            "already_in_clan": "You are already in a clan.",
            "not_found": "Clan not found.",
            "full": f"This clan is full. Maximum members: **{CLAN_MAX_MEMBERS}**.",
            "invite_required": "This clan is invite-only. You need an active invite.",
        }
        await safe_send(ctx, f"❌ {messages.get(status, 'Could not join clan.')}", ephemeral=True)
        return

    await safe_send(ctx, f"✅ {ctx.author.mention} joined **[{clan_data['tag']}] {clan_data['name']}**.")


@clan.sub_command(name="leave", description="Leave your clan")
async def clan_leave(ctx: disnake.ApplicationCommandInteraction):
    success, status = leave_clan(ctx.author.id)
    if not success:
        messages = {
            "not_in_clan": "You are not in a clan.",
            "leader": "Leader cannot leave the clan until leadership is transferred.",
        }
        await safe_send(ctx, f"❌ {messages.get(status, 'Could not leave clan.')}", ephemeral=True)
        return

    await safe_send(ctx, f"✅ {ctx.author.mention} left the clan.")


@clan.sub_command(name="transfer", description="Transfer clan leadership")
async def clan_transfer(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="New leader"),
):
    success, status = transfer_clan_leadership(ctx.author.id, user.id)
    if not success:
        messages = {
            "not_in_clan": "You are not in a clan.",
            "not_leader": "Only the clan leader can transfer leadership.",
            "self": "You are already the leader.",
            "target_not_member": "This user is not a member of your clan.",
        }
        await safe_send(ctx, f"❌ {messages.get(status, 'Could not transfer leadership.')}", ephemeral=True)
        return

    await safe_send(ctx, f"✅ {ctx.author.mention} transferred clan leadership to {user.mention}.")


@clan.sub_command(name="info", description="Show clan profile")
async def clan_info(ctx: disnake.ApplicationCommandInteraction):
    clan_data = get_user_clan(ctx.author.id)
    if not clan_data:
        await safe_send(ctx, "❌ You are not in a clan.", ephemeral=True)
        return

    members = get_clan_members(clan_data["clan_id"])
    weekly = get_clan_weekly_contributions(clan_data["clan_id"])
    needed = get_clan_next_level_xp(clan_data["level"])
    xp_text = "MAX" if needed is None else f"{clan_data['xp']:,}/{needed:,}"

    embed = disnake.Embed(
        title=f"[{clan_data['tag']}] {clan_data['name']}",
        description=clan_data.get("description") or "No description set.",
        color=EMBED_COLOR,
    )
    embed.add_field(name="Level", value=f"{clan_data['level']}/{CLAN_MAX_LEVEL}", inline=True)
    embed.add_field(name="XP", value=xp_text, inline=True)
    embed.add_field(name="Access", value="Public" if clan_data["access"] == "public" else "Invite only", inline=True)
    embed.add_field(name="Active Boosts", value=f"Mining Efficiency: **+{format_clan_bonus(clan_data['level'])}** ore sale value", inline=False)

    member_lines = []
    for member in members:
        try:
            user = await bot.fetch_user(int(member["user_id"]))
            name = user.display_name
        except (ValueError, disnake.DiscordException):
            name = f"User {member['user_id']}"
        member_lines.append(f"**{member['rank']}** - {name} ({member['total_xp']:,} XP)")
    embed.add_field(name=f"Members ({len(members)}/{CLAN_MAX_MEMBERS})", value="\n".join(member_lines) or "None", inline=False)

    weekly_lines = []
    for row in weekly[:10]:
        try:
            user = await bot.fetch_user(int(row["user_id"]))
            name = user.display_name
        except (ValueError, disnake.DiscordException):
            name = f"User {row['user_id']}"
        weekly_lines.append(f"{name}: **{row['xp']:,} XP**")
    embed.add_field(name="Weekly XP", value="\n".join(weekly_lines) or "No XP this week.", inline=False)
    await safe_send(ctx, embed=embed)


@clan.sub_command(name="edit", description="Edit clan settings")
async def clan_edit(
    ctx: disnake.ApplicationCommandInteraction,
    tag: str = commands.Param(default=None, description="New clan tag", min_length=2, max_length=6),
    description: str = commands.Param(default=None, description="New clan description", max_length=180),
    access: str = commands.Param(default=None, choices=["public", "invite"], description="Clan access"),
):
    normalized_tag = tag.strip().upper() if tag else None
    normalized_description = description.strip() if description is not None else None
    success, status, clan_data = update_clan_settings(
        ctx.author.id,
        tag=normalized_tag,
        description=normalized_description,
        access=access,
    )
    if not success:
        messages = {
            "not_in_clan": "You are not in a clan.",
            "not_leader": "Only the clan leader can edit clan settings.",
            "nothing": "Set at least one field to edit.",
        }
        await safe_send(ctx, f"❌ {messages.get(status, 'Could not edit clan.')}", ephemeral=True)
        return

    await safe_send(ctx, f"✅ Clan settings updated: **[{clan_data['tag']}] {clan_data['name']}**.")


@clan.sub_command(name="top", description="Show clan leaderboard")
async def clan_top(
    ctx: disnake.ApplicationCommandInteraction,
    page: int = commands.Param(default=1, ge=1, description="Page number"),
):
    clans = get_clan_top(limit=100)
    if not clans:
        await safe_send(ctx, "No clans yet.")
        return

    per_page = 10
    total_pages = (len(clans) + per_page - 1) // per_page
    page = min(page, total_pages)
    start = (page - 1) * per_page
    page_clans = clans[start:start + per_page]

    lines = []
    for idx, clan_data in enumerate(page_clans, start=start + 1):
        lines.append(
            f"{idx}. **[{clan_data['tag']}] {clan_data['name']}** • "
            f"Level {clan_data['level']} • {clan_data['total_xp']:,} XP"
        )

    embed = disnake.Embed(
        title="Clan Leaderboard",
        description="\n".join(lines),
        color=EMBED_COLOR,
    )
    embed.set_footer(text=f"Page {page}/{total_pages}")
    await safe_send(ctx, embed=embed)


@clan.sub_command(name="invite", description="Invite a user to your clan")
async def clan_invite(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="User to invite"),
):
    if user.bot:
        await safe_send(ctx, "❌ You cannot invite bots.", ephemeral=True)
        return
    success, status, clan_data = create_clan_invite(ctx.author.id, user.id)
    if not success:
        messages = {
            "not_in_clan": "You are not in a clan.",
            "target_in_clan": "This user is already in a clan.",
        }
        await safe_send(ctx, f"❌ {messages.get(status, 'Could not create invite.')}", ephemeral=True)
        return

    await safe_send(
        ctx,
        f"✅ {user.mention} was invited to **[{clan_data['tag']}] {clan_data['name']}**. "
        "They will receive the join prompt the next time they use the bot.",
    )


@bot.listen("on_application_command_completion")
async def notify_pending_clan_invite(ctx: disnake.ApplicationCommandInteraction):
    invite = activate_pending_clan_invite(ctx.author.id)
    if not invite:
        return

    expires_ts = int(datetime.fromisoformat(invite["expires_at"]).timestamp())
    await safe_send(
        ctx,
        f"📨 You were invited to **[{invite['tag']}] {invite['name']}**. "
        f"Use `/clan join name:{invite['name']}` before <t:{expires_ts}:R>.",
        ephemeral=True,
    )
