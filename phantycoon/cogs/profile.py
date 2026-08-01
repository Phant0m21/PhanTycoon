from datetime import datetime

import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import CURRENCY, EMBED_COLOR
from phantycoon.data import LAPIS_EMOJI, PICKAXES, UPGRADES
from phantycoon.database import get_active_boosts, get_user_businesses, get_user_clan, get_user_data
from phantycoon.progression import BOOSTS
from phantycoon.interactions import safe_defer, safe_embed, safe_send


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
        value=f"{user_data['wallet']} {CURRENCY}\n{user_data['lapis']} {LAPIS_EMOJI}",
        inline=False,
    )

    current_pickaxe = user_data.get("current_pickaxe", "Stone Pickaxe")
    pickaxe_emoji = PICKAXES.get(current_pickaxe, {}).get("emoji", "")
    embed.add_field(
        name="Pickaxe",
        value=f"{pickaxe_emoji} {current_pickaxe}\nMine cooldown: **{get_mine_cooldown(target.id):.1f}s**",
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


def get_mine_cooldown(user_id):
    user_data = get_user_data(user_id)
    base = PICKAXES.get(user_data.get("current_pickaxe", "Stone Pickaxe"), {}).get("cooldown", 4.2)
    level = user_data.get("time_management_level", 0)
    reduction = sum(row["mine_reduction"] for row in UPGRADES["time_management"]["levels"][:level])
    cooldown = max(0.5, base - reduction)
    if "mine_haste" in get_active_boosts(user_id):
        cooldown = max(0.5, cooldown * BOOSTS["mine_haste"]["value"])
    return cooldown


def build_buffs_embed(target):
    data = get_user_data(target.id)
    tm_level = data.get("time_management_level", 0)
    tm_rows = UPGRADES["time_management"]["levels"][:tm_level]
    mine_reduction = sum(row["mine_reduction"] for row in tm_rows)
    work_reduction = sum(row["work_reduction_minutes"] for row in tm_rows)
    business_level = data.get("business_optimization_level", 0)
    business_bonus = sum(row["income_bonus"] for row in UPGRADES["business_optimization"]["levels"][:business_level])
    miner_level = data.get("miner_boost_level", 0)
    ore_bonus = sum(row["ore_bonus"] for row in UPGRADES["miner_boost"]["levels"][:miner_level])
    clan = get_user_clan(target.id)
    clan_bonus = clan["level"] * 0.5 if clan else 0
    active_boosts = get_active_boosts(target.id)

    lines = [
        f"**Pickaxe** {data.get('current_pickaxe', 'Stone Pickaxe')} • {get_mine_cooldown(target.id):.1f}s • {PICKAXES[data.get('current_pickaxe', 'Stone Pickaxe')].get('rolls_min', 1)}–{PICKAXES[data.get('current_pickaxe', 'Stone Pickaxe')].get('rolls_max', 1)} rolls",
        f"**Time Management L{tm_level}** • Mine −{mine_reduction:.1f}s • Work −{work_reduction}m",
        f"**Business Optimization L{business_level}** • Collect +{business_bonus}%",
        f"**Ore Miner L{miner_level}** • Ore value +{ore_bonus}%",
        f"**Commanding Manager L{data.get('prestige_manager_level', 0)}** • Income +{data.get('prestige_manager_level', 0) * 20}%",
        f"**Starting Capital L{data.get('prestige_capital_level', 0)}**",
        f"**Double Vein L{data.get('prestige_double_ore_level', 0)}** • Double chance {data.get('prestige_double_ore_level', 0) * 8}%",
        f"**Diamond Rush L{data.get('prestige_ore_value_level', 0)}** • Ore value +{data.get('prestige_ore_value_level', 0) * 20}%",
        f"**Clan** • Ore value +{clan_bonus:.1f}%" if clan else "**Clan** • Inactive",
    ]
    if active_boosts:
        boost_lines = []
        for boost_id, expires_at in active_boosts.items():
            boost = BOOSTS.get(boost_id)
            if boost:
                boost_lines.append(f"**{boost['name']}** • {boost['effect']} • <t:{int(datetime.fromisoformat(expires_at).timestamp())}:R>")
        if boost_lines:
            lines.extend(boost_lines)
    else:
        lines.append("**Temporary boosts** • Inactive")
    embed = disnake.Embed(title=f"Buffs — {target.name}", description="\n".join(lines), color=EMBED_COLOR)
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
    embed.description = (
        f"Registered **{registered}**\n"
        f"Earned **{user_data['total_earned']:,}{CURRENCY}** • Spent **{user_data['total_spent']:,}{CURRENCY}**\n"
        f"Work **{user_data['work_earned']:,}{CURRENCY}** ({user_data['work_count']:,}) • "
        f"Business **{user_data['collect_earned']:,}{CURRENCY}**\n"
        f"Mines **{user_data['mine_count']:,}** • Games **{user_data['games_played']:,}**"
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    return embed


class ProfileView(disnake.ui.View):
    def __init__(self, author_id, target_id=None, mode="profile"):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.target_id = target_id
        self.mode = mode
        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(ProfileButton("Profile", "profile", disnake.ButtonStyle.primary))
        self.add_item(ProfileButton("Stats", "stats", disnake.ButtonStyle.primary))
        self.add_item(ProfileButton("Buffs", "buffs", disnake.ButtonStyle.primary))

    async def update_embed(self, inter: disnake.MessageInteraction):
        target = await inter.bot.fetch_user(self.target_id or inter.author.id)
        builders = {"profile": build_profile_embed, "stats": build_stats_embed, "buffs": build_buffs_embed}
        embed = builders[self.mode](target)
        self.update_buttons()
        await safe_send(inter, embed=embed, view=ProfileView(inter.author.id, target.id, self.mode))

class ProfileButton(disnake.ui.Button):
    def __init__(self, label, mode, style):
        super().__init__(label=label, style=style, custom_id=f"profile_{mode}")
        self.mode = mode

    async def callback(self, inter: disnake.MessageInteraction):
        if self.view.author_id is not None and inter.author.id != self.view.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return

        await safe_defer(inter, with_message=False)
        if self.view.author_id is None:
            view = ProfileView(inter.author.id, inter.author.id, self.mode)
            target = await inter.bot.fetch_user(inter.author.id)
            builders = {"profile": build_profile_embed, "stats": build_stats_embed, "buffs": build_buffs_embed}
            await safe_send(inter, embed=builders[self.mode](target), view=view)
            return
        self.view.mode = self.mode
        target = await inter.bot.fetch_user(self.view.target_id)
        builders = {"profile": build_profile_embed, "stats": build_stats_embed, "buffs": build_buffs_embed}
        await safe_send(inter, embed=builders[self.mode](target), view=ProfileView(inter.author.id, target.id, self.mode))


@bot.slash_command(name="profile", description="Show user profile")
async def profile(
    ctx: disnake.ApplicationCommandInteraction,
    user: disnake.User = commands.Param(default=None, description="User"),
):
    target = user or ctx.author
    view = ProfileView(ctx.author.id, target.id, mode="profile")
    await safe_defer(ctx)
    view.message = await safe_send(ctx, embed=build_profile_embed(target), view=view)
