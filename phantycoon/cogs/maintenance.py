import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import DEV_ID, EMBED_COLOR
from phantycoon.database import clear_maintenance_reason, get_maintenance_reason, set_maintenance_reason
from phantycoon.interactions import safe_embed


def is_developer(inter):
    return inter.author.id == DEV_ID


@bot.slash_command_check
async def maintenance_check(ctx: disnake.ApplicationCommandInteraction):
    if is_developer(ctx):
        return True

    reason = get_maintenance_reason()
    if not reason:
        return True

    embed = disnake.Embed(
        title="PhanTycoon is temporarily closed",
        description=f"**Reason:** {reason}",
        color=EMBED_COLOR,
    )
    await ctx.response.send_message(embed=embed, ephemeral=True)
    return False


@bot.slash_command(name="maintenance", description="Developer maintenance mode")
async def maintenance(ctx: disnake.ApplicationCommandInteraction):
    pass


@maintenance.sub_command(name="enable", description="Block bot usage for everyone except the developer")
async def maintenance_enable(
    ctx: disnake.ApplicationCommandInteraction,
    reason: str = commands.Param(description="Reason shown to users", max_length=500),
):
    if not is_developer(ctx):
        await safe_embed(ctx, "Access denied", "Only the developer can use this command.", ephemeral=True)
        return

    set_maintenance_reason(reason.strip() or "Maintenance is in progress.")
    await safe_embed(ctx, "Maintenance enabled", f"Users are now blocked from using PhanTycoon.\n**Reason:** {get_maintenance_reason()}", ephemeral=True)


@maintenance.sub_command(name="disable", description="Allow users to use the bot again")
async def maintenance_disable(ctx: disnake.ApplicationCommandInteraction):
    if not is_developer(ctx):
        await safe_embed(ctx, "Access denied", "Only the developer can use this command.", ephemeral=True)
        return

    clear_maintenance_reason()
    await safe_embed(ctx, "Maintenance disabled", "Users can use PhanTycoon again.", ephemeral=True)


@maintenance.sub_command(name="status", description="Show current maintenance mode status")
async def maintenance_status(ctx: disnake.ApplicationCommandInteraction):
    if not is_developer(ctx):
        await safe_embed(ctx, "Access denied", "Only the developer can use this command.", ephemeral=True)
        return

    reason = get_maintenance_reason()
    if reason:
        await safe_embed(ctx, "Maintenance active", f"**Reason:** {reason}", ephemeral=True)
    else:
        await safe_embed(ctx, "Maintenance inactive", "Users can currently use PhanTycoon.", ephemeral=True)
