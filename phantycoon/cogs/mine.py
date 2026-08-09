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
from phantycoon.interactions import safe_defer, safe_embed, safe_send
from phantycoon.cogs.captcha import block_if_captcha_active, generate_captcha_code, send_captcha
from phantycoon.cogs.maintenance import block_if_maintenance_active
from phantycoon.progression import add_quest_rewards_to_embed, boost_multiplier, record_quest_event


MINE_TIPS = (
    "Sell ore with the **Sell ore** button: Ore Miner, Diamond Rush and your clan bonus all increase the final sale price.",
    "Better pickaxes unlock rarer ore and perform more mining rolls, but every pickaxe adds the same **1.1-second** delay.",
    "Open `/profile` → **Buffs** to see every active multiplier, its exact value and your current mine cooldown.",
    "Joining a clan increases the value of every ore you sell. The bonus grows by **0.5% per clan level**.",
    "The **Double Vein** prestige upgrade rolls separately for every ore find, so it becomes stronger with high-tier pickaxes.",
    "Ore Miner and Diamond Rush multiply ore value together with the clan bonus; improving different sources scales better over time.",
    "You can keep using **Mine again** on an old mine message—even after a long break or a bot restart—without entering `/mine` again.",
    "Early upgrades are intentionally inexpensive. Buy a few Ore Miner levels before saving for the next pickaxe to speed up progression.",
    "Time Management affects both `/work` and `/mine`, making it useful even when you alternate between active mining and timed income.",
    "Mining cooldown has a hard floor of **2.0 seconds**. Further cooldown bonuses cannot reduce it below that.",
    "Mine Haste reduces your mining cooldown by **35%**, but the **2.0-second** minimum still applies.",
    "Mining Frenzy increases every ore quantity you find by **50%** for its duration.",
    "Prospector increases the final sale value of ore by **40%**; save a large batch and sell it while the boost is active.",
    "The Stone Pickaxe finds Coal and Copper; Iron becomes available with the Iron Pickaxe.",
    "The Golden Pickaxe unlocks Gold, while the Diamond Pickaxe is the first one that can find Diamonds.",
    "The Netherite Pickaxe has **5–7 rolls per mine**, the highest roll count of all pickaxes.",
    "A mining roll chooses one available ore, so several rolls can combine into a larger stack of the same ore.",
    "Ore stays in your inventory until you sell it; there is no need to sell after every mining action.",
    "Check `/inventory` to see your stored ore and switch to a pickaxe you own.",
    "Pickaxes are equipped from `/inventory`; buying one does not automatically replace your equipped pickaxe.",
    "Do not sell a pickaxe you still want to use: pickaxes sell for only half their shop price, while ore has no storage limit.",
    "Daily quests award Lapis Lazuli. Mining, collecting ore and selling ore can each advance different quest objectives.",
    "Daily quests have three reward tiers, so continuing the same objective can unlock more Lapis Lazuli.",
    "Quest difficulty scales with your progress, but newly generated quests only ask for ores your equipped pickaxe can find.",
    "Every successful mine contributes **5 Clan XP** when you belong to a clan.",
    "Clan levels improve ore sale value for every member, so regular mining benefits the whole clan.",
    "Commanding Manager improves `/work` and `/collect`; it does not increase the value of ore.",
    "Diamond Rush and Ore Miner affect ore sale prices, not the amount of ore found.",
    "Double Vein affects ore quantity, while Mining Frenzy can increase that resulting quantity again.",
    "The chance shown for an ore is used only among ores unlocked by your current pickaxe.",
    "Prestige requires a high-tier pickaxe, businesses, completed jobs and enough wallet balance; check `/prestige reset` for what is missing.",
    "Prestige resets ordinary progress but awards an Ender Eye used for permanent upgrades in `/prestige shop`.",
    "Business Optimization affects `/collect`, while Commanding Manager boosts both `/work` and business income. Their bonuses serve different systems.",
    "If a captcha appears, solve it with `/verify code`. The code is case-sensitive; `/verify_regen` replaces an unreadable image.",
)


def mine_embed(user, pickaxe_name, results, quest_rewards=None):
    found = "\n".join(f"{ORES[name]['emoji']} {name} x{amount}" for name, amount in results.items())
    emoji = PICKAXES.get(pickaxe_name, {}).get("emoji", "")
    embed = disnake.Embed(
        title="Mine",
        description=f"{found}\n{emoji} **{pickaxe_name}**",
        color=EMBED_COLOR,
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    if random.random() < 0.03:
        embed.add_field(name="**Useful tip**", value=random.choice(MINE_TIPS), inline=False)
    add_quest_rewards_to_embed(embed, quest_rewards or [])
    return embed


async def run_mine(inter):
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
    await safe_send(inter, embed=mine_embed(inter.author, pickaxe_name, results, quest_rewards), view=MineView(inter.author.id))
    if captcha_triggered:
        await send_captcha(inter, captcha_code)


class MineView(disnake.ui.View):
    def __init__(self, author_id=None):
        super().__init__(timeout=None)
        self.author_id = author_id

    async def interaction_check(self, inter):
        if await block_if_maintenance_active(inter):
            return False
        # After a restart persistent legacy buttons become personal shortcuts for whoever clicks.
        if self.author_id is not None and inter.author.id != self.author_id:
            await safe_embed(inter, "Error", "This is not your menu.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="Mine again", style=disnake.ButtonStyle.primary, custom_id="mine:again")
    async def mine_button(self, button, inter):
        await run_mine(inter)

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
        embed = disnake.Embed(title="Ore Sale", description=f"Earned: **+{total_earned:,}{CURRENCY}**\nOre sold: **{total_sold:,}**", color=EMBED_COLOR)
        quest_rewards = record_quest_event(inter.author.id, "ore_sales", total_sold)
        quest_rewards += record_quest_event(inter.author.id, "ore_sale_value", total_earned)
        add_quest_rewards_to_embed(embed, quest_rewards)
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        await safe_send(inter, embed=embed, view=MineView(inter.author.id))


@bot.listen("on_ready")
async def register_mine_view():
    if not getattr(bot, "_mine_view_registered", False):
        bot.add_view(MineView())
        bot._mine_view_registered = True


@bot.slash_command(name="mine", description="Go mining")
async def mine(ctx: disnake.ApplicationCommandInteraction):
    await run_mine(ctx)
