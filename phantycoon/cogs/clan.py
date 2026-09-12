from datetime import datetime, timezone

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import CURRENCY, EMBED_COLOR
from phantycoon.database import *
from phantycoon.cogs.maintenance import block_if_maintenance_active
from phantycoon.interactions import safe_edit, safe_embed, safe_send


def format_clan_bonus(level):
    return f"{level * 0.5:.1f}%"


def normalize_clan_tag(tag):
    tag = tag.strip()
    if not tag or any(character.isspace() for character in tag):
        return None
    if any(character in "[]" for character in tag):
        return None
    if "<:" in tag or "<a:" in tag or ">" in tag:
        return None
    return tag.upper()


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
        member_lines = []
        for position, member in enumerate(members, start=1):
            try:
                user = await bot.fetch_user(int(member["user_id"]))
                name = user.display_name
            except (ValueError, disnake.DiscordException):
                name = f"User {member['user_id']}"
            leader = " — **Leader**" if member["rank"] == "Leader" else ""
            member_lines.append(
                f"{position}. [{clan_data['tag']}] **{name}**{leader} · **{member['total_xp']:,} XP**"
            )
        description = clan_data.get("description") or "No clan description yet."
        embed.description = (
            f"*{description}*\n"
            f"Access: **{access}**\n\n"
            f"Clan Level: **{clan_data['level']}/{CLAN_MAX_LEVEL}** · **{xp_text} XP** to next level\n"
            f"Ore sell price bonus: **+{format_clan_bonus(clan_data['level'])}**\n"
            f"Members: **{len(members)}/{CLAN_MAX_MEMBERS}**\n\n"
            + "\n".join(member_lines)
        )
    elif mode == "members":
        lines = []
        for member in members:
            try:
                user = await bot.fetch_user(int(member["user_id"]))
                name = user.display_name
            except (ValueError, disnake.DiscordException):
                name = f"User {member['user_id']}"
            lines.append(f"**[{clan_data['tag']}] {name}**\nRank: **{member['rank']}**\nTotal XP: **{member['total_xp']:,}**")
        embed.description = "\n".join(lines) or "No members."
    else:
        embed.title = f"[{clan_data['tag']}] {clan_data['name']} - Weekly Clan"
        weekly = get_clan_weekly_contributions(clan_data["clan_id"])
        lines = []
        for row in weekly[:10]:
            try:
                user = await bot.fetch_user(int(row["user_id"]))
                name = user.display_name
            except (ValueError, disnake.DiscordException):
                name = f"User {row['user_id']}"
            lines.append(f"**[{clan_data['tag']}] {name}**\nContributed XP: **{row['xp']:,}**")
        embed.description = "\n".join(lines) or "No weekly XP."
    return embed


class ClanView(disnake.ui.View):
    def __init__(self, author_id, mode="overview"):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.mode = mode
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(ClanButton("Info", "overview", disnake.ButtonStyle.primary))
        self.add_item(ClanButton("Weekly Clan", "weekly", disnake.ButtonStyle.primary))

    async def update_embed(self, inter):
        self.update_buttons()
        await safe_edit(inter, embed=await build_clan_embed(self.author_id, self.mode), view=self)


class ClanButton(disnake.ui.Button):
    def __init__(self, label, mode, style):
        super().__init__(label=label, style=style, custom_id=f"clan_{mode}")
        self.mode = mode

    async def callback(self, inter):
        if await block_if_maintenance_active(inter):
            return
        if self.view.author_id is None:
            self.view.author_id = inter.author.id
        elif inter.author.id != self.view.author_id:
            await safe_embed(inter, "Error", "This is not your clan menu.", ephemeral=True)
            return
        self.view.mode = self.mode
        await self.view.update_embed(inter)


@bot.slash_command(name="clan", description="Clan commands")
async def clan(ctx: disnake.ApplicationCommandInteraction):
    pass


@clan.sub_command(name="create", description="Create a clan")
async def clan_create(
    ctx: disnake.ApplicationCommandInteraction,
    name: str = commands.Param(description="Clan name", min_length=3, max_length=32),
    tag: str = commands.Param(description="Clan tag (standard Discord emoji supported)", min_length=1, max_length=16),
):
    normalized_tag = normalize_clan_tag(tag)
    if not normalized_tag:
        await safe_embed(ctx, "Error", "Clan tags cannot contain spaces, brackets, or custom Discord emoji. Standard Discord emoji are supported.", ephemeral=True)
        return
    success, status, clan_data = create_clan(ctx.author.id, name.strip(), normalized_tag)
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
    embed.add_field(name="Cost", value=f"{CLAN_CREATE_COST:,} {CURRENCY}", inline=False)
    embed.add_field(name="Access", value="Public", inline=False)
    embed.add_field(name="Mining Efficiency", value=format_clan_bonus(clan_data["level"]), inline=False)
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
            "banned": "You are permanently banned from this clan.",
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

    await safe_send(ctx, embed=await build_clan_embed(ctx.author.id), view=ClanView(ctx.author.id))


@clan.sub_command(name="edit", description="Edit clan settings")
async def clan_edit(
    ctx: disnake.ApplicationCommandInteraction,
    tag: str = commands.Param(default=None, description="New clan tag (standard Discord emoji supported)", min_length=1, max_length=16),
    description: str = commands.Param(default=None, description="New clan description", max_length=180),
    access: str = commands.Param(default=None, choices=["public", "invite"], description="Clan access"),
):
    normalized_tag = normalize_clan_tag(tag) if tag else None
    if tag is not None and not normalized_tag:
        await safe_embed(ctx, "Error", "Clan tags cannot contain spaces, brackets, or custom Discord emoji. Standard Discord emoji are supported.", ephemeral=True)
        return
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


class ClanDeleteView(disnake.ui.View):
    def __init__(self, leader_id, clan_id, clan_name):
        super().__init__(timeout=60)
        self.leader_id = leader_id
        self.clan_id = clan_id
        self.clan_name = clan_name

    async def interaction_check(self, inter):
        if await block_if_maintenance_active(inter):
            return False
        if inter.author.id != self.leader_id:
            await safe_embed(inter, "Error", "Only the clan leader who started this confirmation can use it.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="Delete clan", style=disnake.ButtonStyle.danger)
    async def confirm_delete(self, button, inter):
        success, status, _ = delete_clan(inter.author.id, self.clan_id)
        if not success:
            messages = {
                "not_in_clan": "You are no longer in a clan.",
                "not_leader": "Only the current clan leader can delete the clan.",
                "clan_changed": "Your clan changed after this confirmation was created.",
            }
            await safe_edit(inter, embed=disnake.Embed(title="Clan not deleted", description=messages.get(status, "The clan could not be deleted."), color=EMBED_COLOR), view=None)
            return
        await safe_edit(inter, embed=disnake.Embed(title="Clan deleted", description=f"**{self.clan_name}** and all of its clan data were permanently deleted.", color=EMBED_COLOR), view=None)

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.secondary)
    async def cancel_delete(self, button, inter):
        await safe_edit(inter, embed=disnake.Embed(title="Deletion cancelled", description=f"**{self.clan_name}** was not deleted.", color=EMBED_COLOR), view=None)


@clan.sub_command(name="delete", description="Permanently delete your clan")
async def clan_delete(ctx: disnake.ApplicationCommandInteraction):
    clan_data = get_user_clan(ctx.author.id)
    if not clan_data:
        await safe_embed(ctx, "Error", "You are not in a clan.", ephemeral=True)
        return
    if clan_data["rank"] != "Leader":
        await safe_embed(ctx, "Error", "Only the clan leader can delete the clan.", ephemeral=True)
        return
    embed = disnake.Embed(
        title="Delete clan?",
        description=(
            f"Are you sure you want to permanently delete **[{clan_data['tag']}] {clan_data['name']}**?\n\n"
            "All members, XP, invites, bans, and leaderboard progress belonging to this clan will be deleted. This cannot be undone."
        ),
        color=EMBED_COLOR,
    )
    await safe_send(ctx, embed=embed, view=ClanDeleteView(ctx.author.id, clan_data["clan_id"], clan_data["name"]), ephemeral=True)


@clan.sub_command(name="ban", description="Permanently ban and remove a clan member")
async def clan_ban(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="Clan member to ban"),
):
    if user.bot:
        await safe_embed(ctx, "Error", "Bots cannot be clan members.", ephemeral=True)
        return
    success, status, clan_data = ban_clan_member(ctx.author.id, user.id)
    if not success:
        messages = {
            "not_in_clan": "You are not in a clan.",
            "not_leader": "Only the clan leader can ban members.",
            "self": "You cannot ban yourself. Use `/clan delete` to delete the clan.",
            "target_not_member": "This user is not a member of your clan.",
        }
        await safe_embed(ctx, "Error", messages.get(status, "Could not ban this member."), ephemeral=True)
        return
    await safe_embed(ctx, "Member banned", f"{user.mention} was removed and permanently banned from **[{clan_data['tag']}] {clan_data['name']}**.")


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
            f"{idx}. [{clan_data['tag']}] {clan_data['name']} - "
            f"**Level {clan_data['level']}** · **{clan_data['total_xp']:,} XP**"
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
            "target_banned": "This user is permanently banned from your clan.",
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
