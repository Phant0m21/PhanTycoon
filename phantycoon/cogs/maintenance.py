import disnake

from phantycoon.bot import bot
from phantycoon.config import DEV_ID, EMBED_COLOR
from phantycoon.database import get_maintenance_reason


def is_developer(inter):
    return inter.author.id == DEV_ID


async def block_if_maintenance_active(inter):
    if is_developer(inter):
        return False

    reason = get_maintenance_reason()
    if not reason:
        return False

    embed = disnake.Embed(
        title="PhanTycoon is temporarily closed",
        description=f"**Reason:** {reason}",
        color=EMBED_COLOR,
    )
    if inter.response.is_done():
        await inter.followup.send(embed=embed, ephemeral=True)
    else:
        await inter.response.send_message(embed=embed, ephemeral=True)
    return True


@bot.slash_command_check
async def maintenance_check(ctx: disnake.ApplicationCommandInteraction):
    return not await block_if_maintenance_active(ctx)



