import disnake
from disnake.ext import commands

from phantycoon.bot import bot
from phantycoon.config import CURRENCY, EMBED_COLOR
from phantycoon.data import PICKAXES, PRESTIGE_TOKEN_EMOJI, PRESTIGE_TOKEN_NAME, PRESTIGE_UPGRADES
from phantycoon.database import *
from phantycoon.interactions import safe_edit, safe_send
from phantycoon.shop_data import load_shop
from phantycoon.state import active_buffs, collect_cooldowns


def get_next_prestige_requirements(user_data):
    next_prestige = user_data.get("prestige_level", 0) + 1
    return {
        "prestige": next_prestige,
        "balance": 1_000_000 * next_prestige,
        "work_count": 250 * next_prestige,
        "pickaxe": "Netherite Pickaxe" if next_prestige >= 3 else "Diamond Pickaxe",
    }


def get_prestige_upgrade_level(user_data, upgrade_id):
    columns = {
        "commanding_manager": "prestige_manager_level",
        "starting_capital": "prestige_capital_level",
        "double_vein": "prestige_double_ore_level",
        "diamond_rush": "prestige_ore_value_level",
    }
    return user_data.get(columns[upgrade_id], 0)


def get_missing_prestige_requirements(user_id):
    user_data = get_user_data(user_id)
    inventory = get_user_inventory(user_id)
    user_businesses = set(get_user_businesses(user_id))
    shop = load_shop()
    all_businesses = set(shop.get("business", {}).keys())
    requirements = get_next_prestige_requirements(user_data)
    total_balance = user_data["wallet"]
    missing = []

    if total_balance < requirements["balance"]:
        missing.append(
            f"Balance: **{total_balance:,}/{requirements['balance']:,} {CURRENCY}**"
        )

    if user_data["work_count"] < requirements["work_count"]:
        missing.append(
            f"Jobs completed: **{user_data['work_count']}/{requirements['work_count']}**"
        )

    missing_businesses = sorted(all_businesses - user_businesses)
    if missing_businesses:
        missing.append("Businesses: **" + ", ".join(missing_businesses) + "**")

    required_pickaxe = requirements["pickaxe"]
    has_required_pickaxe = (
        user_data.get("current_pickaxe") == required_pickaxe
        or inventory.get(required_pickaxe, 0) > 0
    )
    if not has_required_pickaxe:
        emoji = PICKAXES.get(required_pickaxe, {}).get("emoji", "")
        missing.append(f"Pickaxe: **{emoji} {required_pickaxe}**")

    return missing, requirements


def build_prestige_shop_embed(user):
    user_data = get_user_data(user.id)
    inventory = get_user_inventory(user.id)
    token_count = inventory.get(PRESTIGE_TOKEN_NAME, 0)

    embed = disnake.Embed(
        title="Prestige Shop",
        description=f"Balance: {PRESTIGE_TOKEN_EMOJI} **{token_count}**\nEach upgrade costs {PRESTIGE_TOKEN_EMOJI} **1**.",
        color=EMBED_COLOR,
    )

    for upgrade_id, upgrade_data in PRESTIGE_UPGRADES.items():
        level = get_prestige_upgrade_level(user_data, upgrade_id)
        max_level = upgrade_data["max_level"]
        embed.add_field(
            name=f"{upgrade_data['name']} ({level}/{max_level})",
            value=upgrade_data["description"],
            inline=False,
        )

    embed.set_thumbnail(url=user.display_avatar.url)
    return embed


class PrestigeShopView(disnake.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.refresh_buttons()

    def refresh_buttons(self):
        self.clear_items()
        user_data = get_user_data(self.author_id)
        for upgrade_id, upgrade_data in PRESTIGE_UPGRADES.items():
            level = get_prestige_upgrade_level(user_data, upgrade_id)
            max_level = upgrade_data["max_level"]
            self.add_item(
                PrestigeUpgradeButton(
                    upgrade_id=upgrade_id,
                    label=f"{upgrade_data['name']} ({level}/{max_level})",
                    disabled=level >= max_level,
                )
            )


class PrestigeUpgradeButton(disnake.ui.Button):
    def __init__(self, upgrade_id, label, disabled):
        super().__init__(
            label=label,
            style=disnake.ButtonStyle.primary,
            custom_id=f"prestige_upgrade_{upgrade_id}",
            disabled=disabled,
        )
        self.upgrade_id = upgrade_id

    async def callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.view.author_id:
            await safe_send(inter, "❌ This is not your prestige shop.", ephemeral=True)
            return

        success, status, level = buy_prestige_upgrade(inter.author.id, self.upgrade_id)
        upgrade = PRESTIGE_UPGRADES[self.upgrade_id]
        if not success:
            if status == "currency":
                await safe_send(
                    inter,
                    f"❌ You need {PRESTIGE_TOKEN_EMOJI} **1** to buy this upgrade.",
                    ephemeral=True,
                )
            else:
                await safe_send(inter, "❌ This upgrade is already maxed.", ephemeral=True)
            return

        self.view.refresh_buttons()
        embed = build_prestige_shop_embed(inter.author)
        await safe_edit(inter, embed=embed, view=self.view)
        await safe_send(
            inter,
            f"✅ **{upgrade['name']}** upgraded to level **{level}**.",
            ephemeral=True,
        )


@bot.slash_command(name="prestige_reset", description="Reset your progress and gain prestige currency")
async def prestige_reset(ctx: disnake.ApplicationCommandInteraction):
    missing, requirements = get_missing_prestige_requirements(ctx.author.id)
    if missing:
        embed = disnake.Embed(
            title="Prestige Requirements",
            description=(
                f"Next prestige: **{requirements['prestige']}**\n\n"
                "Missing requirements:\n" + "\n".join(f"• {item}" for item in missing)
            ),
            color=EMBED_COLOR,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await safe_send(ctx, embed=embed, ephemeral=True)
        return

    new_prestige, token_count, starting_cash = prestige_reset_user(ctx.author.id)
    active_buffs.pop(ctx.author.id, None)
    collect_cooldowns.pop(ctx.author.id, None)

    embed = disnake.Embed(
        title="Prestige Reset Complete",
        description=(
            f"{ctx.author.mention} reached prestige **{new_prestige}**.\n"
            f"Received: {PRESTIGE_TOKEN_EMOJI} **1 {PRESTIGE_TOKEN_NAME}**\n"
            f"Prestige currency balance: {PRESTIGE_TOKEN_EMOJI} **{token_count}**"
        ),
        color=EMBED_COLOR,
    )
    if starting_cash > 0:
        embed.add_field(
            name="Starting Capital",
            value=f"You started with **{starting_cash:,} {CURRENCY}**.",
            inline=False,
        )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await safe_send(ctx, embed=embed)


@bot.slash_command(name="prestige_shop", description="Buy permanent prestige upgrades")
async def prestige_shop(ctx: disnake.ApplicationCommandInteraction):
    embed = build_prestige_shop_embed(ctx.author)
    await safe_send(ctx, embed=embed, view=PrestigeShopView(ctx.author.id))
