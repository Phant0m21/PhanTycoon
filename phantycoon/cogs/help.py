import disnake

from phantycoon.bot import bot
from phantycoon.config import EMBED_COLOR
from phantycoon.cogs.maintenance import block_if_maintenance_active
from phantycoon.interactions import safe_defer, safe_edit, safe_embed, safe_send


class HelpSelect(disnake.ui.Select):
    def __init__(self, author_id):
        self.author_id = author_id
        options = [
            disnake.SelectOption(label="Economy", value="economy", description="Earn, spend, and track your progress"),
            disnake.SelectOption(label="Activities", value="games", description="Mining and quick games"),
            disnake.SelectOption(label="Clans", value="clans", description="Build and manage your clan"),
            disnake.SelectOption(label="Profile", value="profile", description="View your account and quests"),
            disnake.SelectOption(label="Utility", value="utils", description="Helpful bot commands"),
        ]
        super().__init__(placeholder="Choose a category", options=options, custom_id="help_select")

    async def callback(self, inter: disnake.MessageInteraction):
        if await block_if_maintenance_active(inter):
            return
        if self.author_id is not None and inter.author.id != self.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return

        category = inter.values[0]
        embed = disnake.Embed(color=EMBED_COLOR)

        if category == "economy":
            embed.title = "Economy"
            embed.add_field(name="/balance", value="Check your wallet and bank balance.", inline=False)
            embed.add_field(name="/work", value="Work to earn cash after a cooldown.", inline=False)
            embed.add_field(name="/collect", value="Collect income from your businesses.", inline=False)
            embed.add_field(name="/shop open", value="Browse items, pickaxes, and upgrades.", inline=False)
            embed.add_field(name="/buy", value="Buy an available shop item.", inline=False)
            embed.add_field(name="/top", value="View the global leaderboard.", inline=False)

        elif category == "games":
            embed.title = "Activities"
            embed.add_field(name="/mine", value="Mine ores and add them to your inventory.", inline=False)
            embed.add_field(name="/coinflip", value="Flip a coin for a chance to win.", inline=False)

        elif category == "clans":
            embed.title = "Clans"
            embed.add_field(name="/clan create", value="Create your own clan.", inline=False)
            embed.add_field(name="/clan join", value="Join an available clan.", inline=False)
            embed.add_field(name="/clan leave", value="Leave your current clan.", inline=False)
            embed.add_field(name="/clan info", value="View a clan's details and members.", inline=False)
            embed.add_field(name="/clan top", value="View the clan leaderboard.", inline=False)
            embed.add_field(name="/clan invite", value="Invite a user to your clan.", inline=False)

        elif category == "profile":
            embed.title = "Profile"
            embed.add_field(name="/profile", value="View your profile, upgrades, and statistics.", inline=False)
            embed.add_field(name="/inventory", value="View and equip your items and pickaxe.", inline=False)
            embed.add_field(name="/quests", value="View your daily quests and rewards.", inline=False)
            embed.add_field(name="/prestige reset", value="Reset progress for a permanent prestige reward.", inline=False)
            embed.add_field(name="/prestige shop", value="Spend prestige currency on permanent upgrades.", inline=False)

        elif category == "utils":
            embed.title = "Utility"
            embed.add_field(name="/ping", value="Check the bot's latency and uptime.", inline=False)
            embed.add_field(name="/verify", value="Complete an active security verification.", inline=False)
            embed.add_field(name="/verify_regen", value="Generate a new verification code.", inline=False)
            embed.add_field(name="/support", value="Get a link to the official support server.", inline=False)

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
    view.add_item(disnake.ui.Button(label="Join", url="https://discord.gg/5S8qpKEzTB"))
    await safe_send(ctx, embed=embed, view=view)
