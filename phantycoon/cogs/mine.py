import random
from datetime import datetime, timezone

import disnake

from phantycoon.bot import bot
from phantycoon.config import CURRENCY, EMBED_COLOR
from phantycoon.data import ORES, PICKAXES, UPGRADES
from phantycoon.database import (
    CLAN_MINE_XP, can_mine, get_clan_ore_bonus_multiplier, get_mine_result,
    get_prestige_ore_value_multiplier, get_user_data, get_user_inventory,
    grant_clan_xp, record_mine_for_captcha, update_last_mine, update_stats,
    update_user_inventory, update_user_wallet,
)
from phantycoon.interactions import safe_defer, safe_edit, safe_embed, safe_send
from phantycoon.cogs.captcha import block_if_captcha_active, generate_captcha_code, send_captcha
from phantycoon.progression import add_quest_rewards_to_embed, boost_multiplier, record_quest_event


MINE_TIPS = (
    "Sell ore with the **Sell ore** button: Ore Miner, Diamond Rush and your clan bonus all increase the final sale price.",
    "A better pickaxe does more than unlock rare ore: it also performs more mining rolls per click and lowers the cooldown.",
    "Open `/profile` → **Buffs** to see every active multiplier, its exact value and your current mine cooldown.",
    "Joining a clan increases the value of every ore you sell. The bonus grows by **0.5% per clan level**.",
    "The **Double Vein** prestige upgrade rolls separately for every ore find, so it becomes stronger with high-tier pickaxes.",
    "Ore Miner and Diamond Rush multiply ore value together with the clan bonus; improving different sources scales better over time.",
    "You can keep using **Mine again** on an old mine message—even after a long break or a bot restart—without entering `/mine` again.",
    "Early upgrades are intentionally inexpensive. Buy a few Ore Miner levels before saving for the next pickaxe to speed up progression.",
    "Time Management affects both `/work` and `/mine`, making it useful even when you alternate between active mining and timed income.",
    "Do not sell a pickaxe you still want to use: pickaxes sell for only half their shop price, while ore has no storage limit.",
    "Business Optimization affects `/collect`, while Commanding Manager boosts both `/work` and business income. Their bonuses serve different systems.",
    "If a captcha appears, solve it with `/verify code`. The code is case-sensitive; `/verify_regen` replaces an unreadable image.",
)


def mine_embed(user, pickaxe_name, results, quest_rewards=None):
    found = " • ".join(f"{ORES[name]['emoji']} {name} x{amount}" for name, amount in results.items())
    emoji = PICKAXES.get(pickaxe_name, {}).get("emoji", "")
    embed = disnake.Embed(
        title="Mine",
        description=f"{found}\n{emoji} **{pickaxe_name}**",
        color=EMBED_COLOR,
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    if random.random() < 0.05:
        embed.add_field(name="💡 Useful tip", value=random.choice(MINE_TIPS), inline=False)
    add_quest_rewards_to_embed(embed, quest_rewards or [])
    return embed


async def run_mine(inter, *, edit_message=False):
    if await block_if_captcha_active(inter):
        return
    can, next_time, _ = can_mine(inter.author.id)
    if not can:
        wait_seconds = max(1, int((next_time - datetime.now(timezone.utc)).total_seconds()))
        await safe_embed(inter, "Mine", f"You are mining too fast. Wait **{wait_seconds} sec.**", ephemeral=True)
        return

    await safe_defer(inter)
    user_data = get_user_data(inter.author.id)
    pickaxe_name = user_data.get("current_pickaxe", "Stone Pickaxe")
    results = get_mine_result(pickaxe_name, inter.author.id)
    inventory = get_user_inventory(inter.author.id)
    for ore_name, amount in results.items():
        inventory[ore_name] = inventory.get(ore_name, 0) + amount
    update_user_inventory(inter.author.id, inventory)
    update_last_mine(inter.author.id)
    update_stats(inter.author.id, mine_count=1)
    clan_progress = grant_clan_xp(inter.author.id, CLAN_MINE_XP)
    captcha_triggered, captcha_code = record_mine_for_captcha(inter.author.id, generate_captcha_code)
    quest_rewards = []
    quest_rewards += record_quest_event(inter.author.id, "mine_actions", 1)
    quest_rewards += record_quest_event(inter.author.id, "ore_units", sum(results.values()))
    quest_rewards += record_quest_event(inter.author.id, "distinct_ores", len(results))
    if clan_progress:
        quest_rewards += record_quest_event(inter.author.id, "clan_xp", CLAN_MINE_XP)
    for ore_name, amount in results.items():
        quest_rewards += record_quest_event(inter.author.id, f"ore_{ore_name.lower()}", amount)
    result_embed = mine_embed(inter.author, pickaxe_name, results, quest_rewards)
    if edit_message:
        await safe_edit(inter, embed=result_embed, view=MineView(inter.author.id))
    else:
        await safe_send(inter, embed=result_embed, view=MineView(inter.author.id))
    if captcha_triggered:
        await send_captcha(inter, captcha_code)


class MineView(disnake.ui.View):
    def __init__(self, author_id=None):
        super().__init__(timeout=None)
        self.author_id = author_id

    async def interaction_check(self, inter):
        # After a restart persistent legacy buttons become personal shortcuts for whoever clicks.
        if self.author_id is not None and inter.author.id != self.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="Mine again", style=disnake.ButtonStyle.primary, custom_id="mine:again")
    async def mine_button(self, button, inter):
        await run_mine(inter, edit_message=True)

    @disnake.ui.button(label="Sell ore", style=disnake.ButtonStyle.primary, custom_id="mine:sell")
    async def sell_ores_button(self, button, inter):
        if await block_if_captcha_active(inter):
            return
        inventory = get_user_inventory(inter.author.id)
        user_data = get_user_data(inter.author.id)
        miner_level = user_data.get("miner_boost_level", 0)
        ore_bonus = sum(level["ore_bonus"] for level in UPGRADES["miner_boost"]["levels"][:miner_level])
        prestige_multiplier = get_prestige_ore_value_multiplier(user_data)
        clan_multiplier = get_clan_ore_bonus_multiplier(inter.author.id)
        total_earned = 0
        total_sold = 0
        sold_items = []
        for ore_name, quantity in list(inventory.items()):
            if ore_name not in ORES or quantity <= 0:
                continue
            ore = ORES[ore_name]
            price = int(random.randint(ore["price_min"], ore["price_max"]) * (1 + ore_bonus / 100) * prestige_multiplier * clan_multiplier * boost_multiplier(inter.author.id, "prospector"))
            earned = price * quantity
            total_earned += earned
            total_sold += quantity
            sold_items.append(f"{ore['emoji']} {ore_name} x{quantity} = {earned:,} {CURRENCY}")
            del inventory[ore_name]
        if not total_earned:
            await safe_embed(inter, "Ore Sale", "You do not have any ore to sell.", ephemeral=True)
            return
        await safe_defer(inter)
        update_user_inventory(inter.author.id, inventory)
        update_user_wallet(inter.author.id, user_data["wallet"] + total_earned)
        update_stats(inter.author.id, total_earned=total_earned)
        embed = disnake.Embed(title="Ore Sale", description=f"**+{total_earned:,}{CURRENCY}** • {total_sold:,} ore sold", color=EMBED_COLOR)
        quest_rewards = record_quest_event(inter.author.id, "ore_sales", total_sold)
        quest_rewards += record_quest_event(inter.author.id, "ore_sale_value", total_earned)
        add_quest_rewards_to_embed(embed, quest_rewards)
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        await safe_edit(inter, embed=embed, view=MineView(inter.author.id))

    @disnake.ui.button(label="Profile", style=disnake.ButtonStyle.primary, custom_id="mine:profile")
    async def profile_button(self, button, inter):
        from phantycoon.cogs.profile import ProfileView, build_profile_embed
        await safe_edit(inter, embed=build_profile_embed(inter.author), view=ProfileView(inter.author.id, inter.author.id))

    @disnake.ui.button(label="Quests", style=disnake.ButtonStyle.primary, custom_id="mine:quests")
    async def quests_button(self, button, inter):
        from phantycoon.cogs.quests import build_quests_embed
        from phantycoon.navigation import NavigationView
        await safe_edit(inter, embed=build_quests_embed(inter.author.id), view=NavigationView())

    @disnake.ui.button(label="Shop", style=disnake.ButtonStyle.primary, custom_id="mine:shop")
    async def shop_button(self, button, inter):
        from phantycoon.cogs.shop import ShopView
        embed = disnake.Embed(title="Shop", description="Select a category.", color=EMBED_COLOR)
        await safe_edit(inter, embed=embed, view=ShopView(inter.author.id))


@bot.listen("on_ready")
async def register_mine_view():
    if not getattr(bot, "_mine_view_registered", False):
        bot.add_view(MineView())
        bot._mine_view_registered = True


@bot.slash_command(name="mine", description="Go mining")
async def mine(ctx: disnake.ApplicationCommandInteraction):
    await run_mine(ctx)
