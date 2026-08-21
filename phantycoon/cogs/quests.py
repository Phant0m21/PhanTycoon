from datetime import datetime, timedelta, timezone

import disnake

from phantycoon.bot import bot
from phantycoon.config import EMBED_COLOR
from phantycoon.cogs.maintenance import block_if_maintenance_active
from phantycoon.cogs.shop import shop
from phantycoon.data import LAPIS_EMOJI
from phantycoon.database import get_active_boosts, get_user_data, purchase_boost
from phantycoon.interactions import safe_edit, safe_embed, safe_send
from phantycoon.progression import BOOSTS, QUEST_DEFINITIONS, SPECIAL_DAILY_SLOT, ensure_daily_quests, next_quest_reset


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def quest_line(row):
    definition = QUEST_DEFINITIONS[row["quest_key"]]
    completed = row["claimed_tier"] >= 3
    if completed:
        status = "COMPLETED"
        target = row["target_3"]
    else:
        tier = row["claimed_tier"] + 1
        target = row[f"target_{tier}"]
        status = f"{min(row['progress'], target):,}/{target:,}"
    description = definition.get("description", definition["unit"]).format(target=f"{target:,}")
    reward_left = sum(row[f"reward_{tier}"] for tier in range(row["claimed_tier"] + 1, 4))
    return f"**{definition['name']}** `{status}`\n*{description}* · reward left: **{reward_left} {LAPIS_EMOJI}**"


def quest_line(row):
    definition = QUEST_DEFINITIONS[row["quest_key"]]
    completed = row["claimed_tier"] >= 3
    if completed:
        status = "COMPLETED"
        target = row["target_3"]
    else:
        tier = row["claimed_tier"] + 1
        target = row[f"target_{tier}"]
        status = f"{min(row['progress'], target):,}/{target:,}"
    description = definition.get("description", definition["unit"]).format(target=f"{target:,}")
    return f"**{definition['name']}** `{status}`\n*{description}*"


def build_quests_embed(user_id):
    rows = ensure_daily_quests(user_id)
    data = get_user_data(user_id)
    reset_at = next_quest_reset()
    reset_in = format_duration((reset_at - datetime.now(timezone.utc)).total_seconds())
    embed = disnake.Embed(
        title="PhanTycoon Contracts",
        color=EMBED_COLOR,
    )
    daily_rows = [row for row in rows if row["slot"] != SPECIAL_DAILY_SLOT]
    special_rows = [row for row in rows if row["slot"] == SPECIAL_DAILY_SLOT]
    daily_blocks = [quest_line(row) for row in daily_rows]
    special_block = quest_line(special_rows[0]) if special_rows else "No special quest today."
    embed.description = (
        "Daily contracts reset together at **00:00 UTC**. Rewards are random and revealed when a tier is completed.\n\n"
        + "\n\n".join(daily_blocks)
        + "\n\n**High-Value Contract**\n"
        + special_block
        + f"\n\nReset: **{reset_in}** · Wallet Lapis: **{data['lapis']}** {LAPIS_EMOJI}"
    )
    return embed


@bot.slash_command(name="quests", description="View your three daily quests")
async def quests(ctx: disnake.ApplicationCommandInteraction):
    await safe_send(ctx, embed=build_quests_embed(ctx.author.id))


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
        if await block_if_maintenance_active(inter):
            return
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
        embed = build_boost_shop_embed(inter.author.id, f"Activated {boost['name']}")
        await safe_edit(inter, embed=embed, view=self.view)


@shop.sub_command(name="boosts", description="Buy temporary boosts with Lapis Lazuli")
async def shop_boosts(ctx: disnake.ApplicationCommandInteraction):
    await safe_send(ctx, embed=build_boost_shop_embed(ctx.author.id), view=BoostShopView(ctx.author.id))


def build_boost_shop_embed(user_id, notice=None):
    data = get_user_data(user_id)
    active = get_active_boosts(user_id)
    embed = disnake.Embed(
        title="Lapis Boost Shop",
        description=f"Lapis Lazuli: **{data['lapis']}** {LAPIS_EMOJI}" + (f"\n{notice}" if notice else ""),
        color=EMBED_COLOR,
    )
    for boost_id, boost in BOOSTS.items():
        active_text = f"\nActive until <t:{int(datetime.fromisoformat(active[boost_id]).timestamp())}:R>" if boost_id in active else ""
        embed.add_field(
            name=f"{boost['name']} — {boost['cost']} {LAPIS_EMOJI}",
            value=f"{boost['effect']}\nDuration: **{boost['minutes']} minutes**{active_text}", inline=False,
        )
    return embed
