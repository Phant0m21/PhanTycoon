import json
import random
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import tasks

from phantycoon.bot import bot
from phantycoon.config import EMBED_COLOR
from phantycoon.database import get_bot_state, set_bot_state

EVENT_STATE_KEY = "current_seasonal_event"
EVENT_CHANNEL_ID = 1551300709893546222
EVENT_ROLE_ID = 1551300709113139271
EVENT_DURATION = timedelta(hours=3)


EVENTS = (
    {"id": "coal_rush", "title": "Coal Rush", "description": "Coal drops are doubled while mining.", "kind": "mine_ore", "ore": "Coal", "multiplier": 2.0},
    {"id": "copper_rush", "title": "Copper Rush", "description": "Copper drops are doubled while mining.", "kind": "mine_ore", "ore": "Copper", "multiplier": 2.0},
    {"id": "iron_rush", "title": "Iron Rush", "description": "Iron drops are doubled while mining.", "kind": "mine_ore", "ore": "Iron", "multiplier": 2.0},
    {"id": "gold_rush", "title": "Gold Rush", "description": "Gold drops are doubled while mining.", "kind": "mine_ore", "ore": "Gold", "multiplier": 2.0},
    {"id": "diamond_rush", "title": "Diamond Rush", "description": "Diamond drops are doubled while mining.", "kind": "mine_ore", "ore": "Diamond", "multiplier": 2.0},
    {"id": "quartz_rush", "title": "Quartz Rush", "description": "Quartz drops are doubled while mining.", "kind": "mine_ore", "ore": "Quartz", "multiplier": 2.0},
    {"id": "iridium_rush", "title": "Iridium Rush", "description": "Iridium drops are doubled while mining.", "kind": "mine_ore", "ore": "Iridium", "multiplier": 2.0},
    {"id": "rich_veins", "title": "Rich Veins", "description": "All mined ore quantities are increased by 50%.", "kind": "mine_all", "multiplier": 1.5},
    {"id": "deep_veins", "title": "Deep Veins", "description": "All mined ore quantities are doubled.", "kind": "mine_all", "multiplier": 2.0},
    {"id": "swift_pickaxes", "title": "Swift Pickaxes", "description": "Mining cooldowns are reduced by 30%.", "kind": "mine_cooldown", "multiplier": 0.7},
    {"id": "ore_market", "title": "Ore Market Boom", "description": "Selling ore pays 75% more.", "kind": "ore_sale", "multiplier": 1.75},
    {"id": "ore_market_crash", "title": "Ore Market Crash", "description": "Selling ore pays 50% less.", "kind": "ore_sale", "multiplier": 0.5},
    {"id": "miners_payday", "title": "Miner's Payday", "description": "Every successful mining chest pays twice as much cash.", "kind": "mine_cash", "multiplier": 2.0},
    {"id": "work_bonus", "title": "Overtime Bonus", "description": "Work income is increased by 75%.", "kind": "work_income", "multiplier": 1.75},
    {"id": "work_double", "title": "Double Shift", "description": "Work income is doubled.", "kind": "work_income", "multiplier": 2.0},
    {"id": "quick_shift", "title": "Quick Shift", "description": "Work cooldowns are reduced by 35%.", "kind": "work_cooldown", "multiplier": 0.65},
    {"id": "executive_bonus", "title": "Executive Bonus", "description": "Business collections pay 75% more.", "kind": "collect_income", "multiplier": 1.75},
    {"id": "business_boom", "title": "Business Boom", "description": "Business collections are doubled.", "kind": "collect_income", "multiplier": 2.0},
    {"id": "fast_collections", "title": "Fast Collections", "description": "Business collection cooldown is reduced by 35%.", "kind": "collect_cooldown", "multiplier": 0.65},
    {"id": "coinflip_bonus", "title": "Lucky Tables", "description": "Winning coinflips pay 50% more.", "kind": "game_winnings", "multiplier": 1.5},
    {"id": "coinflip_jackpot", "title": "Coinflip Jackpot", "description": "Winning coinflips pay double.", "kind": "game_winnings", "multiplier": 2.0},
    {"id": "lucky_week", "title": "Lucky Week", "description": "Winning minigames pay 25% more.", "kind": "game_winnings", "multiplier": 1.25},
    {"id": "all_income", "title": "Prosperity Hour", "description": "Work and business income are increased by 25%.", "kind": "all_income", "multiplier": 1.25},
    {"id": "mine_and_work", "title": "Production Sprint", "description": "Mining is faster and work pays 35% more.", "kind": "production_sprint", "multiplier": 1.35},
    {"id": "ore_festival", "title": "Ore Festival", "description": "Mining quantities and ore sale prices are increased by 35%.", "kind": "ore_festival", "multiplier": 1.35},
    {"id": "business_festival", "title": "Business Festival", "description": "Collections pay 50% more and refresh faster.", "kind": "business_festival", "multiplier": 1.5},
    {"id": "worker_festival", "title": "Worker Festival", "description": "Work pays 50% more and refreshes faster.", "kind": "worker_festival", "multiplier": 1.5},
    {"id": "common_ore_hour", "title": "Common Ore Hour", "description": "Coal, Copper and Iron drops are doubled.", "kind": "mine_ore_group", "ores": ("Coal", "Copper", "Iron"), "multiplier": 2.0},
    {"id": "rare_ore_hour", "title": "Rare Ore Hour", "description": "Gold, Diamond, Quartz and Iridium drops are doubled.", "kind": "mine_ore_group", "ores": ("Gold", "Diamond", "Quartz", "Iridium"), "multiplier": 2.0},
    {"id": "miners_market", "title": "Miners' Market", "description": "Mining quantities and ore sale prices are increased by 20%.", "kind": "miners_market", "multiplier": 1.2},
    {"id": "grand_payday", "title": "Grand Payday", "description": "Work and business income are doubled.", "kind": "grand_payday", "multiplier": 2.0},
)


def _now():
    return datetime.now(timezone.utc)


def _event_by_id(event_id):
    return next(event for event in EVENTS if event["id"] == event_id)


def get_current_event():
    raw_state = get_bot_state(EVENT_STATE_KEY)
    if not raw_state:
        return None
    try:
        state = json.loads(raw_state)
        expires_at = datetime.fromisoformat(state["expires_at"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if _now() >= expires_at:
        return None
    try:
        event = _event_by_id(state["event_id"])
    except StopIteration:
        return None
    return {**event, "started_at": state["started_at"], "expires_at": state["expires_at"]}


def event_multiplier(kind, default=1.0):
    event = get_current_event()
    if not event:
        return default
    if event["kind"] == kind:
        return event["multiplier"]
    combined_kinds = {
        "work_income": ("all_income", "production_sprint", "worker_festival", "grand_payday"),
        "collect_income": ("all_income", "business_festival", "grand_payday"),
        "game_winnings": (),
        "mine_all": ("ore_festival", "miners_market"),
        "ore_sale": ("ore_festival", "miners_market"),
    }
    if event["kind"] in combined_kinds.get(kind, ()):
        return event["multiplier"]
    return default


def ore_multiplier(ore_name):
    event = get_current_event()
    if not event:
        return 1.0
    if event["kind"] == "mine_ore" and event["ore"] == ore_name:
        return event["multiplier"]
    if event["kind"] == "mine_ore_group" and ore_name in event["ores"]:
        return event["multiplier"]
    return event_multiplier("mine_all")


def apply_ore_multipliers(results):
    return {
        ore_name: max(1, round(amount * ore_multiplier(ore_name)))
        for ore_name, amount in results.items()
    }


def format_event(event=None):
    event = event or get_current_event()
    if not event:
        return "No event is active."
    expires_at = datetime.fromisoformat(event["expires_at"])
    return f"**{event['title']}**\n{event['description']}\nEnds <t:{int(expires_at.timestamp())}:R>"


def _new_event():
    previous = get_current_event()
    choices = [event for event in EVENTS if not previous or event["id"] != previous["id"]]
    return random.choice(choices)


def _save_event(event, started_at):
    expires_at = started_at + EVENT_DURATION
    set_bot_state(EVENT_STATE_KEY, json.dumps({
        "event_id": event["id"],
        "started_at": started_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }))
    return {**event, "started_at": started_at.isoformat(), "expires_at": expires_at.isoformat()}


async def rotate_event_if_needed(force=False):
    current = get_current_event()
    if current and not force:
        return current
    event = _save_event(_new_event(), _now())
    channel = bot.get_channel(EVENT_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(EVENT_CHANNEL_ID)
        except disnake.DiscordException as error:
            print(f"Event audit channel unavailable: {error!r}")
            return event
    try:
        await channel.send(
            content=f"<@&{EVENT_ROLE_ID}>",
            allowed_mentions=disnake.AllowedMentions(roles=True),
        )
        await channel.send(embed=disnake.Embed(
            title=f"New event: {event['title']}",
            description=f"{event['description']}\n\nDuration: **3 hours**",
            color=EMBED_COLOR,
        ))
    except disnake.DiscordException as error:
        print(f"Event audit failed: {error!r}")
    return event


@tasks.loop(hours=3)
async def event_rotation():
    await rotate_event_if_needed(force=True)


@bot.listen("on_ready")
async def start_event_rotation():
    await rotate_event_if_needed()
    if not event_rotation.is_running():
        event_rotation.start()
