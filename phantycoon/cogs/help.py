import disnake

from phantycoon.bot import bot
from phantycoon.config import EMBED_COLOR
from phantycoon.interactions import safe_defer, safe_edit, safe_embed, safe_send


class HelpSelect(disnake.ui.Select):
    def __init__(self, author_id):
        self.author_id = author_id
        options = [
            disnake.SelectOption(label="Core", value="economy", description="Economy commands"),
            disnake.SelectOption(label="Minigames", value="games", description="Games and active actions"),
            disnake.SelectOption(label="Clans", value="clans", description="Clan commands"),
            disnake.SelectOption(label="Utilities", value="utils", description="Utility commands"),
            disnake.SelectOption(label="Administration", value="admin", description="Developer commands"),
        ]
        super().__init__(placeholder="Choose a category", options=options, custom_id="help_select")

    async def callback(self, inter: disnake.MessageInteraction):
        if self.author_id is not None and inter.author.id != self.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return

        category = inter.values[0]
        embed = disnake.Embed(color=EMBED_COLOR)

        if category == "economy":
            embed.title = "Core"
            embed.description = "`/balance` `/work` `/collect` `/top`\n`/shop open` `/shop upgrades` `/shop boosts` `/buy`\n`/inventory` `/profile` `/quests`\n`/prestige reset` `/prestige shop`"

        elif category == "games":
            embed.title = "Minigames"
            embed.description = "`/mine` `/coinflip`"

        elif category == "clans":
            embed.title = "Clans"
            embed.description = "`/clan create` `/clan join` `/clan leave`\n`/clan info` `/clan top` `/clan invite`\n`/clan edit` `/clan transfer`"

        elif category == "utils":
            embed.title = "Utilities"
            embed.description = "`/ping` `/verify` `/verify_regen` `/support`"

        elif category == "admin":
            embed.title = "Administration"
            embed.description = "`/money add` `/money remove` `/money set`\n`/ban add` `/ban list` `/unban` `/restart`"

        await safe_edit(inter, embed=embed, view=self.view)


class HelpView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.add_item(HelpSelect(author_id))


@bot.slash_command(name="help", description="Show command list")
async def help(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="Bot Help",
        description="Select a category.",
        color=EMBED_COLOR,
    )
    await safe_defer(ctx)
    await safe_send(ctx, embed=embed, view=HelpView(ctx.author.id))


@bot.slash_command(name="support", description="Open the support server invite")
async def support(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="Support Server",
        description="Join the Discord support server for help and updates.",
        color=EMBED_COLOR,
    )
    view = disnake.ui.View(timeout=None)
    view.add_item(disnake.ui.Button(label="Join", url="https://discord.gg/8rWEMDg5Dx"))
    await safe_send(ctx, embed=embed, view=view)
