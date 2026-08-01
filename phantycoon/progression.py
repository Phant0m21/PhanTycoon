import random
from datetime import datetime, timedelta, timezone

from phantycoon.data import LAPIS_EMOJI, PICKAXES
from phantycoon.database import (
    advance_daily_quests, get_active_boosts, get_daily_quests, get_user_businesses,
    get_user_clan, get_user_data, replace_daily_quests,
)


QUEST_DURATION = timedelta(hours=24)
REWARD_SETS = ((1, 1, 2), (1, 2, 2), (2, 2, 2))

# Targets are the tier-I baseline. They are multiplied by the player's progression
# score, except for cooldown-limited actions whose target generator has a hard cap.
QUEST_DEFINITIONS = {
    "mine_actions": {"category": "mining", "name": "Persistent Miner", "unit": "mining actions", "base": (20, 50, 100)},
    "ore_units": {"category": "mining", "name": "Ore Haul", "unit": "ore collected", "base": (50, 140, 300)},
    "distinct_ores": {"category": "mining", "name": "Mixed Veins", "unit": "different ore finds", "base": (15, 40, 80)},
    "ore_sales": {"category": "trading", "name": "Ore Merchant", "unit": "ore sold", "base": (40, 120, 260)},
    "ore_sale_value": {"category": "trading", "name": "Profitable Shipment", "unit": "$ earned from ore", "base": (500, 1800, 4500), "money": True},
    "ore_coal": {"category": "ore_hunt", "name": "Coal Contract", "unit": "Coal collected", "base": (30, 90, 180), "ore": "Coal"},
    "ore_copper": {"category": "ore_hunt", "name": "Copper Contract", "unit": "Copper collected", "base": (15, 45, 100), "ore": "Copper"},
    "ore_iron": {"category": "ore_hunt", "name": "Iron Contract", "unit": "Iron collected", "base": (8, 25, 60), "ore": "Iron"},
    "ore_gold": {"category": "ore_hunt", "name": "Gold Rush", "unit": "Gold collected", "base": (3, 9, 20), "ore": "Gold"},
    "ore_diamond": {"category": "ore_hunt", "name": "Diamond Hunter", "unit": "Diamonds collected", "base": (1, 3, 7), "ore": "Diamond"},
    "work_actions": {"category": "work", "name": "Reliable Worker", "unit": "work shifts", "base": (1, 2, 4), "limited": True},
    "work_income": {"category": "work", "name": "Daily Paycheck", "unit": "$ earned from work", "base": (100, 280, 600), "money": True},
    "collect_actions": {"category": "business", "name": "Business Routine", "unit": "business collections", "base": (1, 2, 3), "limited": True, "business": True},
    "collect_income": {"category": "business", "name": "Executive Revenue", "unit": "$ collected from businesses", "base": (200, 800, 2000), "money": True, "business": True},
    "games_played": {"category": "games", "name": "Game Night", "unit": "minigames played", "base": (2, 5, 10)},
    "games_won": {"category": "games", "name": "Winning Streak", "unit": "minigames won", "base": (1, 3, 6)},
    "game_winnings": {"category": "games", "name": "Lucky Profit", "unit": "$ won in minigames", "base": (200, 800, 2000), "money": True},
    "clan_xp": {"category": "clan", "name": "Clan Contributor", "unit": "Clan XP contributed", "base": (30, 90, 200), "clan": True},
    "cash_spent": {"category": "economy", "name": "Smart Investment", "unit": "$ spent in shops", "base": (1000, 5000, 15000), "money": True},
    "upgrades_bought": {"category": "economy", "name": "Improve the Operation", "unit": "upgrades purchased", "base": (1, 2, 3)},
}

BOOSTS = {
    "mining_frenzy": {"name": "Mining Frenzy", "cost": 4, "minutes": 20, "effect": "+50% ore quantity", "value": 1.50},
    "mine_haste": {"name": "Mine Haste", "cost": 5, "minutes": 15, "effect": "−35% mining cooldown", "value": 0.65},
    "prospector": {"name": "Prospector", "cost": 5, "minutes": 20, "effect": "+40% ore sale value", "value": 1.40},
    "overtime": {"name": "Overtime", "cost": 4, "minutes": 25, "effect": "+35% /work income", "value": 1.35},
    "business_surge": {"name": "Business Surge", "cost": 5, "minutes": 25, "effect": "+30% /collect income", "value": 1.30},
    "lucky_streak": {"name": "Lucky Streak", "cost": 4, "minutes": 20, "effect": "+20% minigame winnings", "value": 1.20},
}


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
    now = datetime.now(timezone.utc).isoformat()
    scale = _progression_scale(user_id)
    quests = []
    for slot, key in enumerate(chosen, start=1):
        quests.append({
            "slot": slot, "quest_key": key, "assigned_at": now,
            "targets": _targets(QUEST_DEFINITIONS[key], scale),
            "rewards": random.choice(REWARD_SETS),
        })
    replace_daily_quests(user_id, quests)
    return get_daily_quests(user_id)


def ensure_daily_quests(user_id):
    quests = get_daily_quests(user_id)
    if not quests:
        return generate_daily_quests(user_id)
    assigned = datetime.fromisoformat(quests[0]["assigned_at"])
    if assigned.tzinfo is None:
        assigned = assigned.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= assigned + QUEST_DURATION:
        return generate_daily_quests(user_id)
    return quests


def record_quest_event(user_id, event_key, amount=1):
    ensure_daily_quests(user_id)
    rewards = advance_daily_quests(user_id, event_key, amount)
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
