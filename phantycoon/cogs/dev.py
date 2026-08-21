import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import CURRENCY, DEV_ID, EMBED_COLOR
from phantycoon.data import LAPIS_EMOJI
from phantycoon.database import (
    admin_update_clan,
    clear_maintenance_reason,
    delete_clan_by_id,
    get_clan_by_id,
    get_clan_by_name,
    get_maintenance_reason,
    get_user_data,
    set_maintenance_reason,
    update_stats,
    update_user_lapis,
    update_user_wallet,
)
from phantycoon.interactions import safe_defer, safe_embed, safe_send


def is_dev(ctx):
    return ctx.author.id == DEV_ID


async def require_dev(ctx):
    if is_dev(ctx):
        return True
    await safe_embed(ctx, "Access denied", "This command is developer-only.", ephemeral=True)
    return False


def normalize_clan_tag(tag):
    if tag is None:
        return None
    cleaned = " ".join(tag.strip().split())
    if not cleaned:
        return None
    return cleaned[:16]


def find_clan(clan_id=None, name=None):
    if clan_id is not None:
        return get_clan_by_id(clan_id)
    if name:
        return get_clan_by_name(name.strip())
    return None


@bot.slash_command(name="dev", description="Developer control center")
async def dev(ctx: disnake.ApplicationCommandInteraction):
    pass


@dev.sub_command_group(name="settings", description="Developer settings and admin tools")
async def dev_settings(ctx: disnake.ApplicationCommandInteraction):
    pass


@dev_settings.sub_command(name="panel", description="Show developer settings overview")
async def dev_settings_panel(ctx: disnake.ApplicationCommandInteraction):
    if not await require_dev(ctx):
        return
    reason = get_maintenance_reason()
    embed = disnake.Embed(
        title="Developer Settings",
        description=(
            "`/dev settings money_add` `/money_remove` `/money_set`\n"
            "`/dev settings lapis_add` `/lapis_remove` `/lapis_set`\n"
            "`/dev settings clan_delete` `/clan_edit`\n"
            "`/dev settings maintenance_enable` `/maintenance_disable` `/maintenance_status`"
        ),
        color=EMBED_COLOR,
    )
    embed.add_field(
        name="Maintenance",
        value=f"Active: **{'Yes' if reason else 'No'}**" + (f"\nReason: {reason}" if reason else ""),
        inline=False,
    )
    await safe_send(ctx, embed=embed, ephemeral=True)


@dev_settings.sub_command(name="money_add", description="Add cash to a user")
async def dev_money_add(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="Target user"),
    amount: int = commands.Param(gt=0, description="Cash amount"),
):
    if not await require_dev(ctx):
        return
    await safe_defer(ctx, ephemeral=True)
    data = get_user_data(user.id)
    new_wallet = data["wallet"] + amount
    update_user_wallet(user.id, new_wallet)
    update_stats(user.id, total_earned=amount)
    await safe_send(ctx, f"Added **{amount:,}{CURRENCY}** to {user.mention}. New wallet: **{new_wallet:,}{CURRENCY}**", ephemeral=True)


@dev_settings.sub_command(name="money_remove", description="Remove cash from a user")
async def dev_money_remove(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="Target user"),
    amount: int = commands.Param(gt=0, description="Cash amount"),
):
    if not await require_dev(ctx):
        return
    data = get_user_data(user.id)
    new_wallet = max(0, data["wallet"] - amount)
    update_user_wallet(user.id, new_wallet)
    await safe_send(ctx, f"Removed cash from {user.mention}. New wallet: **{new_wallet:,}{CURRENCY}**", ephemeral=True)


@dev_settings.sub_command(name="money_set", description="Set a user's cash")
async def dev_money_set(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="Target user"),
    amount: int = commands.Param(ge=0, description="New wallet amount"),
):
    if not await require_dev(ctx):
        return
    update_user_wallet(user.id, amount)
    await safe_send(ctx, f"Set {user.mention}'s wallet to **{amount:,}{CURRENCY}**.", ephemeral=True)


@dev_settings.sub_command(name="lapis_add", description="Add Lapis Lazuli to a user")
async def dev_lapis_add(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="Target user"),
    amount: int = commands.Param(gt=0, description="Lapis amount"),
):
    if not await require_dev(ctx):
        return
    data = get_user_data(user.id)
    new_lapis = data["lapis"] + amount
    update_user_lapis(user.id, new_lapis)
    await safe_send(ctx, f"Added **{amount:,} {LAPIS_EMOJI}** to {user.mention}. New lapis: **{new_lapis:,}**", ephemeral=True)


@dev_settings.sub_command(name="lapis_remove", description="Remove Lapis Lazuli from a user")
async def dev_lapis_remove(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="Target user"),
    amount: int = commands.Param(gt=0, description="Lapis amount"),
):
    if not await require_dev(ctx):
        return
    data = get_user_data(user.id)
    new_lapis = max(0, data["lapis"] - amount)
    update_user_lapis(user.id, new_lapis)
    await safe_send(ctx, f"Removed lapis from {user.mention}. New lapis: **{new_lapis:,} {LAPIS_EMOJI}**", ephemeral=True)


@dev_settings.sub_command(name="lapis_set", description="Set a user's Lapis Lazuli")
async def dev_lapis_set(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(description="Target user"),
    amount: int = commands.Param(ge=0, description="New lapis amount"),
):
    if not await require_dev(ctx):
        return
    update_user_lapis(user.id, amount)
    await safe_send(ctx, f"Set {user.mention}'s lapis to **{amount:,} {LAPIS_EMOJI}**.", ephemeral=True)


@dev_settings.sub_command(name="clan_delete", description="Delete any clan by ID or name")
async def dev_clan_delete(
    ctx: disnake.ApplicationCommandInteraction,
    clan_id: int = commands.Param(default=None, description="Clan ID"),
    name: str = commands.Param(default=None, description="Clan name"),
):
    if not await require_dev(ctx):
        return
    clan = find_clan(clan_id, name)
    if not clan:
        await safe_embed(ctx, "Clan not found", "Provide a valid clan ID or clan name.", ephemeral=True)
        return
    deleted, old_clan = delete_clan_by_id(clan["clan_id"])
    if not deleted:
        await safe_embed(ctx, "Clan not deleted", "The clan could not be deleted.", ephemeral=True)
        return
    await safe_send(ctx, f"Deleted clan **[{old_clan['tag']}] {old_clan['name']}** (`{old_clan['clan_id']}`).", ephemeral=True)


@dev_settings.sub_command(name="clan_edit", description="Edit any clan by ID or name")
async def dev_clan_edit(
    ctx: disnake.ApplicationCommandInteraction,
    clan_id: int = commands.Param(default=None, description="Clan ID"),
    lookup_name: str = commands.Param(default=None, description="Current clan name"),
    new_name: str = commands.Param(default=None, description="New clan name"),
    tag: str = commands.Param(default=None, description="New clan tag"),
    description: str = commands.Param(default=None, description="New description"),
    access: str = commands.Param(default=None, choices=["public", "invite"], description="Clan access"),
):
    if not await require_dev(ctx):
        return
    clan = find_clan(clan_id, lookup_name)
    if not clan:
        await safe_embed(ctx, "Clan not found", "Provide a valid clan ID or current clan name.", ephemeral=True)
        return
    success, status, updated = admin_update_clan(
        clan["clan_id"],
        name=new_name.strip() if new_name else None,
        tag=normalize_clan_tag(tag),
        description=description.strip() if description is not None else None,
        access=access,
    )
    if not success:
        messages = {
            "name_taken": "A clan with that name already exists.",
            "nothing": "No clan fields were provided.",
            "not_found": "Clan not found.",
        }
        await safe_embed(ctx, "Clan not edited", messages.get(status, "Could not edit this clan."), ephemeral=True)
        return
    await safe_send(ctx, f"Updated clan **[{updated['tag']}] {updated['name']}** (`{updated['clan_id']}`).", ephemeral=True)


@dev_settings.sub_command(name="maintenance_enable", description="Enable maintenance mode")
async def dev_maintenance_enable(
    ctx: disnake.ApplicationCommandInteraction,
    reason: str = commands.Param(default="Maintenance is in progress.", description="Reason shown to users"),
):
    if not await require_dev(ctx):
        return
    set_maintenance_reason(reason.strip() or "Maintenance is in progress.")
    await safe_send(ctx, f"Maintenance enabled.\nReason: **{get_maintenance_reason()}**", ephemeral=True)


@dev_settings.sub_command(name="maintenance_disable", description="Disable maintenance mode")
async def dev_maintenance_disable(ctx: disnake.ApplicationCommandInteraction):
    if not await require_dev(ctx):
        return
    clear_maintenance_reason()
    await safe_send(ctx, "Maintenance disabled.", ephemeral=True)


@dev_settings.sub_command(name="maintenance_status", description="Show maintenance mode status")
async def dev_maintenance_status(ctx: disnake.ApplicationCommandInteraction):
    if not await require_dev(ctx):
        return
    reason = get_maintenance_reason()
    await safe_send(
        ctx,
        f"Maintenance is **{'enabled' if reason else 'disabled'}**." + (f"\nReason: {reason}" if reason else ""),
        ephemeral=True,
    )
