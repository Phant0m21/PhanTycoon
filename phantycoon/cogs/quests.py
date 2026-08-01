from datetime import datetime, timedelta, timezone

import disnake

from phantycoon.bot import bot
from phantycoon.config import EMBED_COLOR
from phantycoon.cogs.shop import shop
from phantycoon.data import LAPIS_EMOJI
from phantycoon.database import get_active_boosts, get_user_data, purchase_boost
from phantycoon.interactions import safe_defer, safe_embed, safe_send
from phantycoon.progression import BOOSTS, QUEST_DEFINITIONS, QUEST_DURATION, ensure_daily_quests


def build_quests_embed(user_id):
    rows = ensure_daily_quests(user_id)
    data = get_user_data(user_id)
    reset_at = datetime.fromisoformat(rows[0]["assigned_at"]) + QUEST_DURATION
    embed = disnake.Embed(
        title="Daily Quests",
        description=f"Balance: **{data['lapis']}** {LAPIS_EMOJI}\nNew quests <t:{int(reset_at.timestamp())}:R>.",
        color=EMBED_COLOR,
    )
    for row in rows:
        definition = QUEST_DEFINITIONS[row["quest_key"]]
        tier_lines = []
        for tier in range(1, 4):
            target = row[f"target_{tier}"]
            reward = row[f"reward_{tier}"]
            completed = row["claimed_tier"] >= tier
            marker = "✅" if completed else "▫️"
            tier_lines.append(f"{marker} Tier {tier}: **{min(row['progress'], target):,}/{target:,}** {definition['unit']} — {reward} {LAPIS_EMOJI}")
        embed.add_field(name=definition["name"], value="\n".join(tier_lines), inline=False)
    return embed


@bot.slash_command(name="quests", description="View your three daily quests")
async def quests(ctx: disnake.ApplicationCommandInteraction):
    from phantycoon.navigation import NavigationView
    await safe_send(ctx, embed=build_quests_embed(ctx.author.id), view=NavigationView())


class BoostShopView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id
        for boost_id, boost in BOOSTS.items():
            self.add_item(BoostButton(boost_id, f"{boost['name']} — {boost['cost']}"))


class BoostButton(disnake.ui.Button):
    def __init__(self, boost_id, label):
        super().__init__(label=label, style=disnake.ButtonStyle.primary, custom_id=f"boost:{boost_id}")
        self.boost_id = boost_id

    async def callback(self, inter):
        if self.view.author_id is not None and inter.author.id != self.view.author_id:
            await safe_embed(inter, "Error", "This is not your boost shop.", ephemeral=True)
            return
        boost = BOOSTS[self.boost_id]
        success, balance, expires_at = purchase_boost(
            inter.author.id, self.boost_id, boost["cost"], boost["minutes"] * 60
        )
        if not success:
            if expires_at:
                await safe_embed(inter, "Boost already active", f"**{boost['name']}** cannot be extended. It expires <t:{int(expires_at.timestamp())}:R>.", ephemeral=True)
            else:
                await safe_embed(inter, "Not enough Lapis Lazuli", f"You have **{balance}** {LAPIS_EMOJI}, but need **{boost['cost']}**.", ephemeral=True)
            return
        await safe_embed(
            inter, "Boost activated",
            f"**{boost['name']}**: {boost['effect']}\nActive until <t:{int(expires_at.timestamp())}:R>.\nBalance: **{balance}** {LAPIS_EMOJI}",
            ephemeral=True,
        )


@shop.sub_command(name="boosts", description="Buy temporary boosts with Lapis Lazuli")
async def shop_boosts(ctx: disnake.ApplicationCommandInteraction):
    data = get_user_data(ctx.author.id)
    active = get_active_boosts(ctx.author.id)
    embed = disnake.Embed(
        title="Lapis Boost Shop",
        description=f"Balance: **{data['lapis']}** {LAPIS_EMOJI}\nActive boosts cannot be extended or purchased again.",
        color=EMBED_COLOR,
    )
    for boost_id, boost in BOOSTS.items():
        active_text = f"\nActive until <t:{int(datetime.fromisoformat(active[boost_id]).timestamp())}:R>" if boost_id in active else ""
        embed.add_field(
            name=f"{boost['name']} — {boost['cost']} {LAPIS_EMOJI}",
            value=f"{boost['effect']} for **{boost['minutes']} minutes**.{active_text}", inline=False,
        )
    await safe_send(ctx, embed=embed, view=BoostShopView(ctx.author.id))
