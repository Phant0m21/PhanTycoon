from datetime import datetime, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import CURRENCY, EMBED_COLOR
from phantycoon.database import *
from phantycoon.interactions import safe_defer, safe_edit, safe_embed, safe_send


def format_clan_bonus(level):
    return f"{level * 0.5:.1f}%"


async def build_clan_embed(user_id, mode="overview"):
    clan_data = get_user_clan(user_id)
    if not clan_data:
        return disnake.Embed(title="Clan", description="You are not in a clan.", color=EMBED_COLOR)
    members = get_clan_members(clan_data["clan_id"])
    needed = get_clan_next_level_xp(clan_data["level"])
    xp_text = "MAX" if needed is None else f"{clan_data['xp']:,}/{needed:,}"
    embed = disnake.Embed(title=f"[{clan_data['tag']}] {clan_data['name']}", color=EMBED_COLOR)
    if mode == "overview":
        access = "Public" if clan_data["access"] == "public" else "Invite only"
        embed.description = (
            f"Level **{clan_data['level']}/{CLAN_MAX_LEVEL}** • XP **{xp_text}**\n"
            f"Members **{len(members)}/{CLAN_MAX_MEMBERS}** • {access} • Ore **+{format_clan_bonus(clan_data['level'])}**\n"
            f"{clan_data.get('description') or 'No description.'}"
        )
    elif mode == "members":
        lines = []
        for member in members:
            try:
                user = await bot.fetch_user(int(member["user_id"]))
                name = user.display_name
            except (ValueError, disnake.DiscordException):
                name = f"User {member['user_id']}"
            lines.append(f"**{member['rank']}** • {name} • {member['total_xp']:,} XP")
        embed.description = "\n".join(lines) or "No members."
    else:
        weekly = get_clan_weekly_contributions(clan_data["clan_id"])
        lines = []
        for row in weekly[:10]:
            try:
                user = await bot.fetch_user(int(row["user_id"]))
                name = user.display_name
            except (ValueError, disnake.DiscordException):
                name = f"User {row['user_id']}"
            lines.append(f"{name} • **{row['xp']:,} XP**")
        embed.description = "\n".join(lines) or "No weekly XP."
    return embed


class ClanInfoView(disnake.ui.View):
    def __init__(self, author_id=None):
        super().__init__(timeout=None)
        self.author_id = author_id
        for mode in ("overview", "members", "weekly"):
            self.add_item(ClanInfoButton(mode.title(), mode))


class ClanInfoButton(disnake.ui.Button):
    def __init__(self, label, mode):
        super().__init__(label=label, style=disnake.ButtonStyle.primary, custom_id=f"clan_info:{mode}")
        self.mode = mode

    async def callback(self, inter):
        if self.view.author_id is not None and inter.author.id != self.view.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return
        await safe_defer(inter, with_message=False)
        await safe_edit(inter, embed=await build_clan_embed(inter.author.id, self.mode), view=ClanInfoView(inter.author.id))


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
        await safe_embed(ctx, "Error", messages.get(status, "Could not create clan."), ephemeral=True)
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
        await safe_embed(ctx, "Error", messages.get(status, "Could not join clan."), ephemeral=True)
        return

    await safe_embed(ctx, "Success", f"{ctx.author.mention} joined **[{clan_data['tag']}] {clan_data['name']}**.")


@clan.sub_command(name="leave", description="Leave your clan")
async def clan_leave(ctx: disnake.ApplicationCommandInteraction):
    success, status = leave_clan(ctx.author.id)
    if not success:
        messages = {
            "not_in_clan": "You are not in a clan.",
            "leader": "Leader cannot leave the clan until leadership is transferred.",
        }
        await safe_embed(ctx, "Error", messages.get(status, "Could not leave clan."), ephemeral=True)
        return

    await safe_embed(ctx, "Success", f"{ctx.author.mention} left the clan.")


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
        await safe_embed(ctx, "Error", messages.get(status, "Could not transfer leadership."), ephemeral=True)
        return

    await safe_embed(ctx, "Success", f"{ctx.author.mention} transferred clan leadership to {user.mention}.")


@clan.sub_command(name="info", description="Show clan profile")
async def clan_info(ctx: disnake.ApplicationCommandInteraction):
    clan_data = get_user_clan(ctx.author.id)
    if not clan_data:
        await safe_embed(ctx, "Error", "You are not in a clan.", ephemeral=True)
        return

    await safe_send(ctx, embed=await build_clan_embed(ctx.author.id), view=ClanInfoView(ctx.author.id))


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
        await safe_embed(ctx, "Error", messages.get(status, "Could not edit clan."), ephemeral=True)
        return

    await safe_embed(ctx, "Success", f"Clan settings updated: **[{clan_data['tag']}] {clan_data['name']}**.")


@clan.sub_command(name="top", description="Show clan leaderboard")
async def clan_top(
    ctx: disnake.ApplicationCommandInteraction,
    page: int = commands.Param(default=1, ge=1, description="Page number"),
):
    clans = get_clan_top(limit=100)
    if not clans:
        await safe_embed(ctx, "Clan Leaderboard", "No clans yet.")
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
        await safe_embed(ctx, "Error", "You cannot invite bots.", ephemeral=True)
        return
    success, status, clan_data = create_clan_invite(ctx.author.id, user.id)
    if not success:
        messages = {
            "not_in_clan": "You are not in a clan.",
            "target_in_clan": "This user is already in a clan.",
        }
        await safe_embed(ctx, "Error", messages.get(status, "Could not create invite."), ephemeral=True)
        return

    await safe_embed(
        ctx,
        "Clan Invite",
        f"{user.mention} was invited to **[{clan_data['tag']}] {clan_data['name']}**. "
        "The invite is active now and remains valid for 5 minutes.",
    )
    try:
        await user.send(
            embed=disnake.Embed(
                title="Clan Invite",
                description=f"{ctx.author.mention} invited you to **[{clan_data['tag']}] {clan_data['name']}**. "
                            f"Use `/clan join name:{clan_data['name']}` within 5 minutes.",
                color=EMBED_COLOR,
            )
        )
    except disnake.DiscordException:
        pass


@bot.listen("on_application_command_completion")
async def notify_pending_clan_invite(ctx: disnake.ApplicationCommandInteraction):
    invite = activate_pending_clan_invite(ctx.author.id)
    if not invite:
        return

    expires_ts = int(datetime.fromisoformat(invite["expires_at"]).timestamp())
    await safe_embed(
        ctx,
        "Clan Invite",
        f"You were invited to **[{invite['tag']}] {invite['name']}**. "
        f"Use `/clan join name:{invite['name']}` before <t:{expires_ts}:R>.",
        ephemeral=True,
    )
