import random
from datetime import datetime, time, timedelta, timezone

from phantycoon.config import CURRENCY
from phantycoon.data import LAPIS_EMOJI, PICKAXES, UPGRADES
from phantycoon.database import (
    advance_daily_quests, consume_expired_boosts, get_active_boosts, get_daily_quests,
    get_user_businesses, record_quest_tier_completions,
    get_user_clan, get_user_data, get_user_inventory, mark_prestige_ready_notified, replace_daily_quests,
)
from phantycoon.shop_data import load_shop


QUEST_DURATION = timedelta(hours=24)
REWARD_SETS = ((1, 1, 2), (1, 2, 2), (2, 2, 2))
SPECIAL_REWARD_SET = (3, 4, 5)
SPECIAL_DAILY_SLOT = 4
SPECIAL_DAILY_KEYS = (
    "mine_actions", "ore_units", "ore_sales", "ore_sale_value",
    "work_income", "collect_income", "cash_spent", "clan_xp",
)

# Targets are the tier-I baseline. They are multiplied by the player's progression
# score, except for cooldown-limited actions whose target generator has a hard cap.
QUEST_DEFINITIONS = {
    "mine_actions": {"category": "mining", "name": "Daily Mining", "unit": "mining actions", "description": "Mine {target} time(s).", "base": (20, 50, 100)},
    "ore_units": {"category": "mining", "name": "Ore Haul", "unit": "ore collected", "description": "Collect {target} ore.", "base": (50, 140, 300)},
    "distinct_ores": {"category": "mining", "name": "Mixed Veins", "unit": "different ore finds", "description": "Find {target} different ore drops.", "base": (15, 40, 80)},
    "ore_sales": {"category": "trading", "name": "Ore Merchant", "unit": "ore sold", "description": "Sell {target} ore.", "base": (40, 120, 260)},
    "ore_sale_value": {"category": "trading", "name": "Profitable Shipment", "unit": "$ earned from ore", "description": "Earn {target}$ from ore sales.", "base": (500, 1800, 4500), "money": True},
    "ore_coal": {"category": "ore_hunt", "name": "Coal Contract", "unit": "Coal collected", "description": "Collect {target} Coal.", "base": (30, 90, 180), "ore": "Coal"},
    "ore_copper": {"category": "ore_hunt", "name": "Copper Contract", "unit": "Copper collected", "description": "Collect {target} Copper.", "base": (15, 45, 100), "ore": "Copper"},
    "ore_iron": {"category": "ore_hunt", "name": "Iron Contract", "unit": "Iron collected", "description": "Collect {target} Iron.", "base": (8, 25, 60), "ore": "Iron"},
    "ore_gold": {"category": "ore_hunt", "name": "Gold Rush", "unit": "Gold collected", "description": "Collect {target} Gold.", "base": (3, 9, 20), "ore": "Gold"},
    "ore_diamond": {"category": "ore_hunt", "name": "Diamond Hunter", "unit": "Diamonds collected", "description": "Collect {target} Diamonds.", "base": (1, 3, 7), "ore": "Diamond"},
    "ore_quartz": {"category": "ore_hunt", "name": "Quartz Seeker", "unit": "Quartz collected", "description": "Collect {target} Quartz.", "base": (2, 6, 15), "ore": "Quartz"},
    "ore_iridium": {"category": "ore_hunt", "name": "Iridium Prospect", "unit": "Iridium collected", "description": "Collect {target} Iridium.", "base": (1, 2, 5), "ore": "Iridium"},
    "work_actions": {"category": "work", "name": "Reliable Worker", "unit": "work shifts", "description": "Complete {target} work shift(s).", "base": (1, 2, 4), "limited": True},
    "work_income": {"category": "work", "name": "Daily Paycheck", "unit": "$ earned from work", "description": "Earn {target}$ from work.", "base": (100, 280, 600), "money": True},
    "collect_actions": {"category": "business", "name": "Business Routine", "unit": "business collections", "description": "Collect from businesses {target} time(s).", "base": (1, 2, 3), "limited": True, "business": True},
    "collect_income": {"category": "business", "name": "Executive Revenue", "unit": "$ collected from businesses", "description": "Earn {target}$ from businesses.", "base": (200, 800, 2000), "money": True, "business": True},
    "games_played": {"category": "games", "name": "Game Night", "unit": "minigames played", "description": "Play {target} minigame(s).", "base": (2, 5, 10), "quest": False},
    "games_won": {"category": "games", "name": "Winning Streak", "unit": "minigames won", "description": "Win {target} minigame(s).", "base": (1, 3, 6), "quest": False},
    "game_winnings": {"category": "games", "name": "Lucky Profit", "unit": "$ won in minigames", "description": "Win {target}$ from minigames.", "base": (200, 800, 2000), "money": True, "quest": False},
    "clan_xp": {"category": "clan", "name": "Clan Contributor", "unit": "Clan XP contributed", "description": "Contribute {target} Clan XP.", "base": (30, 90, 200), "clan": True},
    "cash_spent": {"category": "economy", "name": "Smart Investment", "unit": "$ spent", "description": "Spend {target}$.", "base": (1000, 5000, 15000), "money": True},
    "upgrades_bought": {"category": "economy", "name": "Improve the Operation", "unit": "upgrades purchased", "description": "Buy {target} upgrade(s).", "base": (1, 2, 3)},
}

BOOSTS = {
    "mining_frenzy": {"name": "Mining Frenzy", "cost": 4, "minutes": 20, "effect": "+50% ore quantity", "value": 1.50},
    "mine_haste": {"name": "Mine Haste", "cost": 5, "minutes": 15, "effect": "−35% mining cooldown", "value": 0.65},
    "prospector": {"name": "Prospector", "cost": 5, "minutes": 20, "effect": "+40% ore sale value", "value": 1.40},
    "work_rush": {
        "name": "Work Rush",
        "cost": 30,
        "minutes": 4,
        "effect": "Sets /work cooldown to 5 seconds",
        "work_cooldown_seconds": 5,
        "required_upgrade": "time_management",
        "required_level": UPGRADES["time_management"]["max_level"],
    },
}


def is_boost_available(user_id, boost_id):
    boost = BOOSTS.get(boost_id)
    if not boost:
        return False
    required_upgrade = boost.get("required_upgrade")
    if not required_upgrade:
        return True
    user_data = get_user_data(user_id)
    return user_data.get(f"{required_upgrade}_level", 0) >= boost["required_level"]


def expired_boost_notice(user_id):
    expired = consume_expired_boosts(user_id)
    if not expired:
        return None
    names = [BOOSTS[boost_id]["name"] for boost_id in expired if boost_id in BOOSTS]
    return "Boost ended: " + ", ".join(f"**{name}**" for name in names) + "." if names else None


def prestige_ready_notice(user_id):
    user_data = get_user_data(user_id)
    if user_data.get("prestige_ready_notified"):
        return None

    next_prestige = user_data.get("prestige_level", 0) + 1
    if user_data.get("wallet", 0) < 1_000_000 * next_prestige:
        return None
    if user_data.get("prestige_work_count", 0) < 250 * next_prestige:
        return None

    shop = load_shop()
    if set(shop.get("business", {})) - set(get_user_businesses(user_id)):
        return None

    required_pickaxe = "Netherite Pickaxe" if next_prestige >= 3 else "Diamond Pickaxe"
    inventory = get_user_inventory(user_id)
    if user_data.get("current_pickaxe") != required_pickaxe and inventory.get(required_pickaxe, 0) <= 0:
        return None

    if not mark_prestige_ready_notified(user_id):
        return None
    return f"All requirements are complete. Use **`/prestige reset`** to reach prestige {next_prestige}."


def add_prestige_ready_notice(embed, user_id):
    notice = prestige_ready_notice(user_id)
    if notice:
        embed.add_field(name="Prestige ready!", value=notice, inline=False)


def _progression_scale(user_id):
    data = get_user_data(user_id)
    standard_levels = sum(data.get(key, 0) for key in (
        "time_management_level", "business_optimization_level", "miner_boost_level"
    ))
    pickaxes = list(PICKAXES)
    pickaxe_tier = pickaxes.index(data.get("current_pickaxe", "Stone Pickaxe")) if data.get("current_pickaxe") in pickaxes else 0
    activity = min(1.0, (data.get("mine_count", 0) + data.get("work_count", 0) * 10) / 2000)
    return min(4.0, 1 + data.get("prestige_level", 0) * 0.30 + standard_levels * 0.035 + pickaxe_tier * 0.12 + activity)


def _eligible_quests(user_id):
    data = get_user_data(user_id)
    available_ores = PICKAXES.get(data.get("current_pickaxe", "Stone Pickaxe"), PICKAXES["Stone Pickaxe"])["ores"]
    businesses = bool(get_user_businesses(user_id))
    clan = bool(get_user_clan(user_id))
    eligible = []
    for key, definition in QUEST_DEFINITIONS.items():
        if definition.get("quest") is False:
            continue
        if definition.get("ore") and definition["ore"] not in available_ores:
            continue
        if definition.get("business") and not businesses:
            continue
        if definition.get("clan") and not clan:
            continue
        eligible.append(key)
    return eligible


def _targets(definition, scale):
    if definition.get("limited"):
        limited_scale = min(1.5, 1 + (scale - 1) * 0.20)
        return tuple(max(1, round(value * limited_scale)) for value in definition["base"])
    effective = 1 + (scale - 1) * (0.75 if definition.get("money") else 0.60)
    return tuple(max(1, round(value * effective)) for value in definition["base"])


def quest_period_start(now=None):
    now = now or datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def next_quest_reset(now=None):
    return quest_period_start(now) + QUEST_DURATION


def _special_targets(definition, scale):
    targets = _targets(definition, scale)
    multiplier = 5 if definition.get("limited") else 8
    if definition.get("money"):
        multiplier = 10
    return tuple(max(1, target * multiplier) for target in targets)


def _quest_reward_type(special=False):
    cash_weight = 0.62 if special else 0.68
    return "cash" if random.random() < cash_weight else "lapis"


def _quest_reward_amount(reward_type, scale, tier, special=False):
    if reward_type == "lapis":
        base = (3, 5, 7) if special else (1, 2, 3)
        spread = (2, 3, 4) if special else (1, 1, 2)
        scale_bonus = min(3, int((scale - 1) * (2 if special else 1.2)))
        return max(1, base[tier - 1] + random.randint(0, spread[tier - 1]) + scale_bonus)

    multiplier = 3.2 if special else 1.0
    low = int((180 + tier * 170) * scale * multiplier)
    high = int((360 + tier * 340) * scale * multiplier)
    return max(50, random.randint(low, max(low + 1, high)))


def _quest_rewards(scale, special=False):
    reward_types = tuple(_quest_reward_type(special) for _ in range(3))
    rewards = tuple(
        _quest_reward_amount(reward_type, scale, tier, special)
        for tier, reward_type in enumerate(reward_types, start=1)
    )
    return rewards, reward_types


def generate_daily_quests(user_id):
    eligible = _eligible_quests(user_id)
    random.shuffle(eligible)
    chosen = []
    used_categories = set()
    for key in eligible:
        category = QUEST_DEFINITIONS[key]["category"]
        if category not in used_categories:
            chosen.append(key)
            used_categories.add(category)
        if len(chosen) == 3:
            break
    if len(chosen) < 3:
        chosen.extend(key for key in eligible if key not in chosen and len(chosen) < 3)
    special_pool = [key for key in eligible if key in SPECIAL_DAILY_KEYS and key not in chosen]
    if not special_pool:
        special_pool = [key for key in eligible if key in SPECIAL_DAILY_KEYS]
    special_key = random.choice(special_pool or eligible)
    now = quest_period_start().isoformat()
    scale = _progression_scale(user_id)
    quests = []
    for slot, key in enumerate(chosen, start=1):
        rewards, reward_types = _quest_rewards(scale)
        quests.append({
            "slot": slot, "quest_key": key, "assigned_at": now,
            "targets": _targets(QUEST_DEFINITIONS[key], scale),
            "rewards": rewards,
            "reward_types": reward_types,
        })
    rewards, reward_types = _quest_rewards(scale, special=True)
    quests.append({
        "slot": SPECIAL_DAILY_SLOT,
        "quest_key": special_key,
        "assigned_at": now,
        "targets": _special_targets(QUEST_DEFINITIONS[special_key], scale),
        "rewards": rewards,
        "reward_types": reward_types,
    })
    replace_daily_quests(user_id, quests)
    return get_daily_quests(user_id)


def ensure_daily_quests(user_id):
    quests = get_daily_quests(user_id)
    if not quests or len(quests) < SPECIAL_DAILY_SLOT:
        return generate_daily_quests(user_id)
    assigned = datetime.fromisoformat(quests[0]["assigned_at"])
    if assigned.tzinfo is None:
        assigned = assigned.replace(tzinfo=timezone.utc)
    if assigned < quest_period_start():
        return generate_daily_quests(user_id)
    return quests


def record_quest_event(user_id, event_key, amount=1):
    if event_key not in QUEST_DEFINITIONS or QUEST_DEFINITIONS[event_key].get("quest") is False:
        return []
    ensure_daily_quests(user_id)
    rewards = advance_daily_quests(user_id, event_key, amount)
    record_quest_tier_completions(user_id, len(rewards))
    for reward in rewards:
        reward["name"] = QUEST_DEFINITIONS[reward["quest_key"]]["name"]
    return rewards


def add_quest_rewards_to_embed(embed, rewards):
    if not rewards:
        return
    lines = [f"**{item['name']} — Tier {item['tier']}**: +{item['lapis']} {LAPIS_EMOJI}" for item in rewards]
    embed.add_field(name="Quest reward unlocked!", value="\n".join(lines), inline=False)


def boost_multiplier(user_id, boost_id):
    if boost_id not in get_active_boosts(user_id):
        return 1.0
    return BOOSTS[boost_id]["value"]


def add_quest_rewards_to_embed(embed, rewards):
    if not rewards:
        return
    lines = []
    for item in rewards:
        if item.get("reward_type") == "cash":
            reward_text = f"+{item['amount']:,}{CURRENCY}"
        else:
            reward_text = f"+{item['amount']:,} {LAPIS_EMOJI}"
        lines.append(f"**{item['name']} — Tier {item['tier']}**: {reward_text}")
    embed.add_field(name="Quest reward unlocked!", value="\n".join(lines), inline=False)
