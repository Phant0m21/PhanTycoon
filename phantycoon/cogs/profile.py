from datetime import datetime

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import CURRENCY, EMBED_COLOR
from phantycoon.data import PICKAXES
from phantycoon.database import get_user_businesses, get_user_clan, get_user_data
from phantycoon.interactions import safe_defer, safe_edit, safe_embed, safe_send


def get_clan_value(user_id):
    clan = get_user_clan(user_id)
    if not clan:
        return "None"
    return f"[{clan['tag']}] {clan['name']} ({clan['rank']})"


def build_profile_embed(target):
    user_data = get_user_data(target.id)
    embed = disnake.Embed(
        title=f"Profile {target.name}",
        color=EMBED_COLOR,
    )
    embed.add_field(
        name="Prestige",
        value=f"{user_data.get('prestige_level', 0)}",
        inline=False,
    )
    embed.add_field(
        name="Clan",
        value=get_clan_value(target.id),
        inline=False,
    )
    embed.add_field(
        name="Balance",
        value=f"{user_data['wallet']} {CURRENCY}",
        inline=False,
    )

    current_pickaxe = user_data.get("current_pickaxe", "Stone Pickaxe")
    pickaxe_emoji = PICKAXES.get(current_pickaxe, {}).get("emoji", "")
    embed.add_field(
        name="Pickaxe",
        value=f"{pickaxe_emoji} {current_pickaxe}",
        inline=False,
    )

    businesses = get_user_businesses(target.id)
    embed.add_field(
        name="Active businesses",
        value="\n".join(businesses) if businesses else "None",
        inline=False,
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    return embed


def build_stats_embed(target):
    user_data = get_user_data(target.id)
    registered_dt = datetime.fromisoformat(user_data["registered_at"])
    months = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December",
    }
    registered = f"{registered_dt.day} {months[registered_dt.month]} {registered_dt.year}"

    embed = disnake.Embed(
        title=f"Stats {target.name}",
        color=EMBED_COLOR,
    )
    embed.add_field(name="Registered", value=registered, inline=False)
    embed.add_field(name="Total earned", value=f"{user_data['total_earned']} {CURRENCY}", inline=False)
    embed.add_field(name="Total spent", value=f"{user_data['total_spent']} {CURRENCY}", inline=False)
    embed.add_field(name="Earned from /work", value=f"{user_data['work_earned']} {CURRENCY}", inline=False)
    embed.add_field(name="Earned from /collect", value=f"{user_data['collect_earned']} {CURRENCY}", inline=False)
    embed.add_field(name="Jobs completed", value=f"{user_data['work_count']}", inline=False)
    embed.add_field(name="Successful mines", value=f"{user_data['mine_count']}", inline=False)
    embed.add_field(name="Minigames played", value=f"{user_data['games_played']}", inline=False)
    embed.set_thumbnail(url=target.display_avatar.url)
    return embed


class ProfileView(disnake.ui.View):
    def __init__(self, author_id, target_id, mode="profile"):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.target_id = target_id
        self.mode = mode
        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(ProfileButton("Profile", "profile", disnake.ButtonStyle.primary if self.mode == "profile" else disnake.ButtonStyle.secondary))
        self.add_item(ProfileButton("Stats", "stats", disnake.ButtonStyle.primary if self.mode == "stats" else disnake.ButtonStyle.secondary))

    async def update_embed(self, inter: disnake.MessageInteraction):
        target = await inter.bot.fetch_user(self.target_id)
        embed = build_profile_embed(target) if self.mode == "profile" else build_stats_embed(target)
        self.update_buttons()
        await safe_edit(inter, embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if not self.message:
            return
        try:
            await self.message.edit(view=self)
        except disnake.HTTPException:
            pass


class ProfileButton(disnake.ui.Button):
    def __init__(self, label, mode, style):
        super().__init__(label=label, style=style, custom_id=f"profile_{mode}")
        self.mode = mode

    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return

        await safe_defer(inter, with_message=False)
        self.view.mode = self.mode
        await self.view.update_embed(inter)


@bot.slash_command(name="profile", description="Show user profile")
async def profile(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(default=None, description="User"),
):
    target = user or ctx.author
    view = ProfileView(ctx.author.id, target.id, mode="profile")
    await safe_defer(ctx)
    view.message = await safe_send(ctx, embed=build_profile_embed(target), view=view)
