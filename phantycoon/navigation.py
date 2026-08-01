import disnake

from phantycoon.config import EMBED_COLOR
from phantycoon.interactions import safe_send


class NavigationView(disnake.ui.View):
    """Compact, restart-safe shortcuts shared by action responses."""

    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Mine", style=disnake.ButtonStyle.primary, custom_id="nav:mine")
    async def mine(self, button, inter):
        from phantycoon.cogs.mine import run_mine
        await run_mine(inter)

    @disnake.ui.button(label="Profile", style=disnake.ButtonStyle.primary, custom_id="nav:profile")
    async def profile(self, button, inter):
        from phantycoon.cogs.profile import ProfileView, build_profile_embed
        await safe_send(inter, embed=build_profile_embed(inter.author), view=ProfileView(inter.author.id, inter.author.id), ephemeral=True)

    @disnake.ui.button(label="Quests", style=disnake.ButtonStyle.primary, custom_id="nav:quests")
    async def quests(self, button, inter):
        from phantycoon.cogs.quests import build_quests_embed
        await safe_send(inter, embed=build_quests_embed(inter.author.id), ephemeral=True)

    @disnake.ui.button(label="Shop", style=disnake.ButtonStyle.primary, custom_id="nav:shop")
    async def shop(self, button, inter):
        from phantycoon.cogs.shop import ShopView
        embed = disnake.Embed(title="Shop", description="Choose a category below.", color=EMBED_COLOR)
        await safe_send(inter, embed=embed, view=ShopView(inter.author.id), ephemeral=True)
