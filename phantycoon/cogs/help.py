import disnake

from phantycoon.bot import bot
from phantycoon.config import EMBED_COLOR
from phantycoon.interactions import safe_defer, safe_edit, safe_send


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
        if inter.author.id != self.author_id:
            await safe_send(inter, "This is not your menu.", ephemeral=True)
            return

        category = inter.values[0]
        embed = disnake.Embed(color=EMBED_COLOR)

        if category == "economy":
            embed.title = "Core"
            embed.description = "Economy commands"
            embed.add_field(name="/balance", value="Show balance", inline=False)
            embed.add_field(name="/work", value="Earn cash", inline=False)
            embed.add_field(name="/collect", value="Collect business income", inline=False)
            embed.add_field(name="/top", value="Show leaderboard", inline=False)
            embed.add_field(name="/shop open", value="Open the shop", inline=False)
            embed.add_field(name="/buy", value="Buy an item", inline=False)
            embed.add_field(name="/inventory", value="Show inventory", inline=False)
            embed.add_field(name="/profile", value="Show profile", inline=False)
            embed.add_field(name="/shop upgrades", value="Buy passive upgrades", inline=False)
            embed.add_field(name="/prestige reset", value="Reset progress for prestige currency", inline=False)
            embed.add_field(name="/prestige shop", value="Buy permanent prestige upgrades", inline=False)

        elif category == "games":
            embed.title = "Minigames"
            embed.description = "Games and active actions"
            embed.add_field(name="/coinflip", value="Flip a coin", inline=False)
            embed.add_field(name="/mine", value="Go mining", inline=False)

        elif category == "clans":
            embed.title = "Clans"
            embed.description = "Clan commands"
            embed.add_field(name="/clan create", value="Create a clan", inline=False)
            embed.add_field(name="/clan join", value="Join a clan", inline=False)
            embed.add_field(name="/clan info", value="Show clan profile", inline=False)
            embed.add_field(name="/clan leave", value="Leave your clan", inline=False)
            embed.add_field(name="/clan edit", value="Edit clan settings", inline=False)
            embed.add_field(name="/clan invite", value="Invite a user to your clan", inline=False)
            embed.add_field(name="/clan transfer", value="Transfer clan leadership", inline=False)
            embed.add_field(name="/clan top", value="Show clan leaderboard", inline=False)

        elif category == "utils":
            embed.title = "Utilities"
            embed.description = "Utility commands"
            embed.add_field(name="/ping", value="Show technical info", inline=False)
            embed.add_field(name="/support", value="Open the support server invite", inline=False)

        elif category == "admin":
            embed.title = "Administration"
            embed.description = "Developer commands"
            embed.add_field(name="/money add", value="Give cash to a user", inline=False)
            embed.add_field(name="/money remove", value="Remove cash from a user", inline=False)
            embed.add_field(name="/money set", value="Set exact balance", inline=False)
            embed.add_field(name="/restart", value="Restart the bot", inline=False)

        await safe_edit(inter, embed=embed, view=self.view)


class HelpView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(author_id))


@bot.slash_command(name="help", description="Show command list")
async def help(ctx: disnake.ApplicationCommandInteraction):
    embed = disnake.Embed(
        title="Bot Help",
        description="Choose a category below to view commands.",
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
    view = disnake.ui.View()
    view.add_item(disnake.ui.Button(label="Join", url="https://discord.gg/puv8hfzZDT"))
    await safe_send(ctx, embed=embed, view=view)
