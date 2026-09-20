import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone

from phantycoon.config import DB_FILE, EMBLEM_COLORS
from phantycoon.data import (
    BASE_MINE_COOLDOWN, MIN_MINE_COOLDOWN, ORES, PICKAXES,
    PICKAXE_COOLDOWN_ADD, PRESTIGE_TOKEN_NAME, PRESTIGE_UPGRADES, UPGRADES,
)

STAT_COLUMNS = {
    "total_earned",
    "total_spent",
    "work_earned",
    "collect_earned",
    "work_count",
    "prestige_work_count",
    "mine_count",
    "games_played",
}

UPGRADE_COLUMNS = {
    "time_management_level",
    "business_optimization_level",
    "miner_boost_level",
}

PRESTIGE_UPGRADE_COLUMNS = {
    "commanding_manager": "prestige_manager_level",
    "starting_capital": "prestige_capital_level",
    "double_vein": "prestige_double_ore_level",
    "diamond_rush": "prestige_ore_value_level",
}

CLAN_MAX_LEVEL = 150
CLAN_CREATE_COST = 5000
CLAN_MAX_MEMBERS = 10
CLAN_WORK_XP = 25
CLAN_MINE_XP = 5
CLAN_INVITE_SECONDS = 300
CAPTCHA_ACTION_INTERVAL = 150
CAPTCHA_TRIGGER_CHANCE = 0.33
CAPTCHA_MAX_ATTEMPTS = 3
CAPTCHA_MAX_REGENS = 5
CAPTCHA_BAN_DAYS = 7


NAME_MIGRATIONS = {
    "Каменная кирка": "Stone Pickaxe",
    "Железная кирка": "Iron Pickaxe",
    "Золотая кирка": "Golden Pickaxe",
    "Алмазная кирка": "Diamond Pickaxe",
    "Незеритовая кирка": "Netherite Pickaxe",
    "Иридиевая кирка": "Iridium Pickaxe",
    "Уголь": "Coal",
    "Медь": "Copper",
    "Железо": "Iron",
    "Золото": "Gold",
    "Алмаз": "Diamond",
    "Кварц": "Quartz",
    "Иридиевая руда": "Iridium",
    "Шаурмичная": "Shawarma Stand",
    "Автомойка": "Car Wash",
    "Компьютерный клуб": "Gaming Cafe",
    "Ночной клуб": "Nightclub",
    "Казино": "Casino",
    "Энергетик": "Energy Drink",
    "Витамины": "Vitamins",
    "Страховка": "Insurance",
    "Золотая Корона": "Golden Crown",
    "Личный Джет": "Private Jet",
}


def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            wallet INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0,
            last_work TEXT,
            last_collect TEXT,
            last_mine TEXT,
            registered_at TEXT,
            total_earned INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            work_earned INTEGER DEFAULT 0,
            collect_earned INTEGER DEFAULT 0,
            work_count INTEGER DEFAULT 0,
            prestige_work_count INTEGER DEFAULT 0,
            mine_count INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            current_pickaxe TEXT DEFAULT 'Stone Pickaxe',
            time_management_level INTEGER DEFAULT 0,
            business_optimization_level INTEGER DEFAULT 0,
            miner_boost_level INTEGER DEFAULT 0,
            prestige_level INTEGER DEFAULT 0,
            prestige_manager_level INTEGER DEFAULT 0,
            prestige_capital_level INTEGER DEFAULT 0,
            prestige_double_ore_level INTEGER DEFAULT 0,
            prestige_ore_value_level INTEGER DEFAULT 0,
            is_captcha_active INTEGER DEFAULT 0,
            captcha_code TEXT DEFAULT NULL,
            captcha_attempts INTEGER DEFAULT 0,
            captcha_regens INTEGER DEFAULT 0,
            captcha_banned_until TEXT DEFAULT NULL,
            captcha_mine_actions INTEGER DEFAULT 0,
            captcha_mine_limit INTEGER DEFAULT 0,
            lapis INTEGER DEFAULT 0,
            emblem_color TEXT DEFAULT 'White',
            prestige_ready_notified INTEGER DEFAULT 0
        )
    """)
    
    # Businesses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            user_id TEXT,
            business_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Inventory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id TEXT,
            item_name TEXT,
            quantity INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            tag TEXT NOT NULL,
            description TEXT DEFAULT '',
            access TEXT DEFAULT 'public',
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            total_xp INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clan_members (
            clan_id INTEGER NOT NULL,
            user_id TEXT NOT NULL UNIQUE,
            rank TEXT NOT NULL DEFAULT 'Member',
            joined_at TEXT NOT NULL,
            total_xp INTEGER DEFAULT 0,
            PRIMARY KEY (clan_id, user_id),
            FOREIGN KEY (clan_id) REFERENCES clans(clan_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clan_weekly_xp (
            clan_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            week_start TEXT NOT NULL,
            xp INTEGER DEFAULT 0,
            PRIMARY KEY (clan_id, user_id, week_start),
            FOREIGN KEY (clan_id) REFERENCES clans(clan_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clan_invites (
            clan_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            inviter_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            notified_at TEXT,
            expires_at TEXT,
            PRIMARY KEY (clan_id, user_id),
            FOREIGN KEY (clan_id) REFERENCES clans(clan_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clan_bans (
            clan_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            banned_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (clan_id, user_id),
            FOREIGN KEY (clan_id) REFERENCES clans(clan_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_bans (
            user_id TEXT PRIMARY KEY,
            moderator_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            is_permanent INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL UNIQUE,
            guild_id TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            ticket_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            closed_at TEXT,
            closed_by TEXT,
            close_reason TEXT,
            status TEXT NOT NULL DEFAULT 'open'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_quests (
            user_id TEXT NOT NULL,
            slot INTEGER NOT NULL,
            quest_key TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            target_1 INTEGER NOT NULL,
            target_2 INTEGER NOT NULL,
            target_3 INTEGER NOT NULL,
            reward_1 INTEGER NOT NULL,
            reward_2 INTEGER NOT NULL,
            reward_3 INTEGER NOT NULL,
            reward_type_1 TEXT NOT NULL DEFAULT 'lapis',
            reward_type_2 TEXT NOT NULL DEFAULT 'lapis',
            reward_type_3 TEXT NOT NULL DEFAULT 'lapis',
            claimed_tier INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, slot)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_boosts (
            user_id TEXT NOT NULL,
            boost_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            PRIMARY KEY (user_id, boost_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row["name"] for row in cursor.fetchall()}
    required_columns = {
        "wallet": "INTEGER DEFAULT 0",
        "bank": "INTEGER DEFAULT 0",
        "last_work": "TEXT",
        "last_collect": "TEXT",
        "last_mine": "TEXT",
        "registered_at": "TEXT",
        "total_earned": "INTEGER DEFAULT 0",
        "total_spent": "INTEGER DEFAULT 0",
        "work_earned": "INTEGER DEFAULT 0",
        "collect_earned": "INTEGER DEFAULT 0",
        "work_count": "INTEGER DEFAULT 0",
        "prestige_work_count": "INTEGER DEFAULT 0",
        "mine_count": "INTEGER DEFAULT 0",
        "games_played": "INTEGER DEFAULT 0",
        "current_pickaxe": "TEXT DEFAULT 'Stone Pickaxe'",
        "time_management_level": "INTEGER DEFAULT 0",
        "business_optimization_level": "INTEGER DEFAULT 0",
        "miner_boost_level": "INTEGER DEFAULT 0",
        "prestige_level": "INTEGER DEFAULT 0",
        "prestige_manager_level": "INTEGER DEFAULT 0",
        "prestige_capital_level": "INTEGER DEFAULT 0",
        "prestige_double_ore_level": "INTEGER DEFAULT 0",
        "prestige_ore_value_level": "INTEGER DEFAULT 0",
        "is_captcha_active": "INTEGER DEFAULT 0",
        "captcha_code": "TEXT DEFAULT NULL",
        "captcha_attempts": "INTEGER DEFAULT 0",
        "captcha_regens": "INTEGER DEFAULT 0",
        "captcha_banned_until": "TEXT DEFAULT NULL",
        "captcha_mine_actions": "INTEGER DEFAULT 0",
        "captcha_mine_limit": "INTEGER DEFAULT 0",
        "lapis": "INTEGER DEFAULT 0",
        "emblem_color": "TEXT DEFAULT 'White'",
        "prestige_ready_notified": "INTEGER DEFAULT 0",
    }
    for column, definition in required_columns.items():
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
            if column == "prestige_work_count":
                cursor.execute("UPDATE users SET prestige_work_count = work_count")

    cursor.execute("PRAGMA table_info(daily_quests)")
    quest_columns = {row["name"] for row in cursor.fetchall()}
    for column in ("reward_type_1", "reward_type_2", "reward_type_3"):
        if column not in quest_columns:
            cursor.execute(f"ALTER TABLE daily_quests ADD COLUMN {column} TEXT NOT NULL DEFAULT 'lapis'")

    cursor.execute("UPDATE users SET wallet = wallet + bank, bank = 0 WHERE bank > 0")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_businesses_user_id ON businesses(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clan_members_user_id ON clan_members(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clan_weekly_week ON clan_weekly_xp(week_start)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clan_invites_user_id ON clan_invites(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clan_bans_user_id ON clan_bans(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_bans_expires_at ON bot_bans(expires_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_owner_status ON tickets(owner_id, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_quests_user ON daily_quests(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_active_boosts_expiry ON active_boosts(expires_at)")

    for old_name, new_name in NAME_MIGRATIONS.items():
        cursor.execute("UPDATE users SET current_pickaxe = ? WHERE current_pickaxe = ?", (new_name, old_name))
        cursor.execute("UPDATE inventory SET item_name = ? WHERE item_name = ?", (new_name, old_name))
        cursor.execute("UPDATE businesses SET business_name = ? WHERE business_name = ?", (new_name, old_name))
    cursor.execute(
        "DELETE FROM inventory WHERE item_name IN ('Energy Drink', 'Vitamins', 'Insurance', 'Golden Crown', 'Private Jet')"
    )
    
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT wallet, bank, last_work, last_collect, last_mine, registered_at, 
               total_earned, total_spent, work_earned, collect_earned, 
               work_count, prestige_work_count, mine_count, games_played, current_pickaxe,
               time_management_level, business_optimization_level, miner_boost_level,
               prestige_level, prestige_manager_level, prestige_capital_level,
               prestige_double_ore_level, prestige_ore_value_level, lapis, emblem_color,
               prestige_ready_notified
        FROM users WHERE user_id = ?
    """, (str(user_id),))
    result = cursor.fetchone()
    
    if not result:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO users (user_id, registered_at, current_pickaxe,
                time_management_level, business_optimization_level, miner_boost_level,
                prestige_level, prestige_manager_level, prestige_capital_level,
                prestige_double_ore_level, prestige_ore_value_level) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(user_id), now, "Stone Pickaxe", 0, 0, 0, 0, 0, 0, 0, 0))
        conn.commit()
        conn.close()
        return {
            "wallet": 0, "bank": 0, "last_work": None, "last_collect": None, "last_mine": None,
            "registered_at": now, "total_earned": 0, "total_spent": 0,
            "work_earned": 0, "collect_earned": 0, "work_count": 0, "prestige_work_count": 0, "mine_count": 0, "games_played": 0,
            "current_pickaxe": "Stone Pickaxe",
            "time_management_level": 0,
            "business_optimization_level": 0,
            "miner_boost_level": 0,
            "prestige_level": 0,
            "prestige_manager_level": 0,
            "prestige_capital_level": 0,
            "prestige_double_ore_level": 0,
            "prestige_ore_value_level": 0,
            "lapis": 0,
            "emblem_color": "White",
            "prestige_ready_notified": 0,
        }
    
    conn.close()
    return {
        "wallet": result[0],
        "bank": result[1],
        "last_work": result[2],
        "last_collect": result[3],
        "last_mine": result[4],
        "registered_at": result[5],
        "total_earned": result[6] if result[6] is not None else 0,
        "total_spent": result[7] if result[7] is not None else 0,
        "work_earned": result[8] if result[8] is not None else 0,
        "collect_earned": result[9] if result[9] is not None else 0,
        "work_count": result[10] if result[10] is not None else 0,
        "prestige_work_count": result[11] if result[11] is not None else 0,
        "mine_count": result[12] if result[12] is not None else 0,
        "games_played": result[13] if result[13] is not None else 0,
        "current_pickaxe": result[14] if result[14] is not None else "Stone Pickaxe",
        "time_management_level": result[15] if result[15] is not None else 0,
        "business_optimization_level": result[16] if result[16] is not None else 0,
        "miner_boost_level": result[17] if result[17] is not None else 0,
        "prestige_level": result[18] if result[18] is not None else 0,
        "prestige_manager_level": result[19] if result[19] is not None else 0,
        "prestige_capital_level": result[20] if result[20] is not None else 0,
        "prestige_double_ore_level": result[21] if result[21] is not None else 0,
        "prestige_ore_value_level": result[22] if result[22] is not None else 0,
        "lapis": result[23] if result[23] is not None else 0,
        "emblem_color": result[24] or "White",
        "prestige_ready_notified": result[25] or 0,
    }

def get_daily_quests(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_quests WHERE user_id = ? ORDER BY slot", (str(user_id),))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def replace_daily_quests(user_id, quests):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_quests WHERE user_id = ?", (str(user_id),))
    for quest in quests:
        cursor.execute(
            """
            INSERT INTO daily_quests
                (user_id, slot, quest_key, assigned_at, target_1, target_2, target_3,
                 reward_1, reward_2, reward_3, reward_type_1, reward_type_2, reward_type_3)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), quest["slot"], quest["quest_key"], quest["assigned_at"],
                *quest["targets"], *quest["rewards"], *quest.get("reward_types", ("lapis", "lapis", "lapis")),
            ),
        )
    conn.commit()
    conn.close()

def advance_daily_quests(user_id, event_key, amount):
    if amount <= 0:
        return []
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM daily_quests WHERE user_id = ? AND quest_key = ?",
        (str(user_id), event_key),
    )
    rewards = []
    for row in cursor.fetchall():
        new_progress = row["progress"] + int(amount)
        new_tier = row["claimed_tier"]
        payouts = {"lapis": 0, "cash": 0}
        for tier in range(row["claimed_tier"] + 1, 4):
            if new_progress < row[f"target_{tier}"]:
                break
            reward_type = row[f"reward_type_{tier}"] or "lapis"
            reward_amount = row[f"reward_{tier}"]
            payouts[reward_type] = payouts.get(reward_type, 0) + reward_amount
            new_tier = tier
            rewards.append({
                "quest_key": event_key,
                "tier": tier,
                "reward_type": reward_type,
                "amount": reward_amount,
                "lapis": reward_amount if reward_type == "lapis" else 0,
                "cash": reward_amount if reward_type == "cash" else 0,
            })
        cursor.execute(
            "UPDATE daily_quests SET progress = ?, claimed_tier = ? WHERE user_id = ? AND slot = ?",
            (new_progress, new_tier, str(user_id), row["slot"]),
        )
        if payouts.get("lapis"):
            cursor.execute("UPDATE users SET lapis = lapis + ? WHERE user_id = ?", (payouts["lapis"], str(user_id)))
        if payouts.get("cash"):
            cursor.execute(
                "UPDATE users SET wallet = wallet + ?, total_earned = total_earned + ? WHERE user_id = ?",
                (payouts["cash"], payouts["cash"], str(user_id)),
            )
    conn.commit()
    conn.close()
    return rewards

def get_active_boosts(user_id):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT boost_id, expires_at FROM active_boosts WHERE user_id = ?", (str(user_id),))
    boosts = {row["boost_id"]: row["expires_at"] for row in cursor.fetchall() if row["expires_at"] > now}
    conn.close()
    return boosts

def consume_expired_boosts(user_id):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT boost_id FROM active_boosts WHERE user_id = ? AND expires_at <= ?",
        (str(user_id), now),
    )
    boost_ids = [row["boost_id"] for row in cursor.fetchall()]
    if boost_ids:
        cursor.execute(
            "DELETE FROM active_boosts WHERE user_id = ? AND expires_at <= ?",
            (str(user_id), now),
        )
        conn.commit()
    conn.close()
    return boost_ids

def set_emblem_color(user_id, color_name):
    if color_name not in EMBLEM_COLORS:
        return False
    get_user_data(user_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET emblem_color = ? WHERE user_id = ?", (color_name, str(user_id)))
    conn.commit()
    conn.close()
    return True

def get_user_emblem_color(user_id):
    data = get_user_data(user_id)
    return EMBLEM_COLORS.get(data.get("emblem_color"), EMBLEM_COLORS["White"])["hex"]

def purchase_boost(user_id, boost_id, cost, duration_seconds):
    get_user_data(user_id)
    now = datetime.now(timezone.utc)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT lapis FROM users WHERE user_id = ?", (str(user_id),))
    balance = cursor.fetchone()["lapis"]
    if balance < cost:
        conn.close()
        return False, balance, None
    cursor.execute(
        "SELECT expires_at FROM active_boosts WHERE user_id = ? AND boost_id = ?",
        (str(user_id), boost_id),
    )
    row = cursor.fetchone()
    if row:
        existing = datetime.fromisoformat(row["expires_at"])
        if existing.tzinfo is None:
            existing = existing.replace(tzinfo=timezone.utc)
        if existing > now:
            conn.close()
            return False, balance, existing
    expires_at = now + timedelta(seconds=duration_seconds)
    cursor.execute("UPDATE users SET lapis = lapis - ? WHERE user_id = ?", (cost, str(user_id)))
    cursor.execute(
        """
        INSERT INTO active_boosts (user_id, boost_id, expires_at) VALUES (?, ?, ?)
        ON CONFLICT(user_id, boost_id) DO UPDATE SET expires_at = excluded.expires_at
        """,
        (str(user_id), boost_id, expires_at.isoformat()),
    )
    conn.commit()
    conn.close()
    return True, balance - cost, expires_at

def update_user_wallet(user_id, new_wallet):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (new_wallet, str(user_id)))
    conn.commit()
    conn.close()

def update_user_lapis(user_id, new_lapis):
    get_user_data(user_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lapis = ? WHERE user_id = ?", (max(0, int(new_lapis)), str(user_id)))
    conn.commit()
    conn.close()

def add_user_lapis(user_id, amount):
    get_user_data(user_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lapis = MAX(0, lapis + ?) WHERE user_id = ?", (int(amount), str(user_id)))
    conn.commit()
    conn.close()

def update_last_work(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_work = ? WHERE user_id = ?", (datetime.now(timezone.utc).isoformat(), str(user_id)))
    conn.commit()
    conn.close()

def update_last_collect(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_collect = ? WHERE user_id = ?", (datetime.now(timezone.utc).isoformat(), str(user_id)))
    conn.commit()
    conn.close()

def update_last_mine(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_mine = ? WHERE user_id = ?", (datetime.now(timezone.utc).isoformat(), str(user_id)))
    conn.commit()
    conn.close()

def update_stats(user_id, **kwargs):
    invalid_columns = set(kwargs) - STAT_COLUMNS
    if invalid_columns:
        raise ValueError(f"Unknown stat columns: {', '.join(sorted(invalid_columns))}")

    conn = get_db()
    cursor = conn.cursor()
    
    set_clause = ", ".join([f"{key} = {key} + ?" for key in kwargs.keys()])
    values = list(kwargs.values())
    values.append(str(user_id))
    
    cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

def get_bot_state(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM bot_state WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else None

def set_bot_state(key, value):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO bot_state (key, value, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, value, now),
    )
    conn.commit()
    conn.close()

def delete_bot_state(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bot_state WHERE key = ?", (key,))
    conn.commit()
    conn.close()

def get_maintenance_reason():
    return get_bot_state("maintenance_reason")

def set_maintenance_reason(reason):
    set_bot_state("maintenance_reason", reason)

def clear_maintenance_reason():
    delete_bot_state("maintenance_reason")

def update_current_pickaxe(user_id, pickaxe_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_pickaxe = ? WHERE user_id = ?", (pickaxe_name, str(user_id)))
    conn.commit()
    conn.close()

def mark_prestige_ready_notified(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET prestige_ready_notified = 1 WHERE user_id = ? AND prestige_ready_notified = 0",
        (str(user_id),),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

def update_upgrade_level(user_id, upgrade_name, level):
    if upgrade_name not in UPGRADE_COLUMNS:
        raise ValueError(f"Unknown upgrade column: {upgrade_name}")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {upgrade_name} = ? WHERE user_id = ?", (level, str(user_id)))
    conn.commit()
    conn.close()

def update_prestige_upgrade_level(user_id, upgrade_id, level):
    if upgrade_id not in PRESTIGE_UPGRADE_COLUMNS:
        raise ValueError(f"Unknown prestige upgrade: {upgrade_id}")

    max_level = PRESTIGE_UPGRADES[upgrade_id]["max_level"]
    if level < 0 or level > max_level:
        raise ValueError(f"Invalid prestige upgrade level: {level}")

    column = PRESTIGE_UPGRADE_COLUMNS[upgrade_id]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {column} = ? WHERE user_id = ?", (level, str(user_id)))
    conn.commit()
    conn.close()

def get_user_inventory(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (str(user_id),))
    results = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in results}

def update_user_inventory(user_id, items):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE user_id = ?", (str(user_id),))
    for item_name, quantity in items.items():
        if quantity > 0:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (str(user_id), item_name, quantity))
    conn.commit()
    conn.close()

def _new_captcha_limit():
    return CAPTCHA_ACTION_INTERVAL

def get_captcha_status(user_id):
    get_user_data(user_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT is_captcha_active, captcha_code, captcha_attempts, captcha_regens,
               captcha_banned_until, captcha_mine_actions, captcha_mine_limit
        FROM users WHERE user_id = ?
        """,
        (str(user_id),),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "is_captcha_active": bool(row["is_captcha_active"]),
        "captcha_code": row["captcha_code"],
        "captcha_attempts": row["captcha_attempts"] or 0,
        "captcha_regens": row["captcha_regens"] or 0,
        "captcha_banned_until": row["captcha_banned_until"],
        "captcha_mine_actions": row["captcha_mine_actions"] or 0,
        "captcha_mine_limit": row["captcha_mine_limit"] or 0,
    }

def create_bot_ban(user_id, moderator_id, reason, expires_at=None):
    now = datetime.now(timezone.utc).isoformat()
    expires_value = expires_at.isoformat() if expires_at else None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO bot_bans (user_id, moderator_id, reason, created_at, expires_at, is_permanent)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            moderator_id = excluded.moderator_id,
            reason = excluded.reason,
            created_at = excluded.created_at,
            expires_at = excluded.expires_at,
            is_permanent = excluded.is_permanent
        """,
        (str(user_id), str(moderator_id), reason, now, expires_value, int(expires_at is None)),
    )
    conn.commit()
    conn.close()
    return get_bot_ban(user_id)

def get_bot_ban(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bot_bans WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    data = dict(row)
    if not data["is_permanent"] and data["expires_at"]:
        expires_at = datetime.fromisoformat(data["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expires_at:
            cursor.execute("DELETE FROM bot_bans WHERE user_id = ?", (str(user_id),))
            conn.commit()
            conn.close()
            return None
    conn.close()
    return data

def remove_bot_ban(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bot_bans WHERE user_id = ?", (str(user_id),))
    removed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removed

def list_active_bans():
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM bot_bans WHERE is_permanent = 0 AND expires_at IS NOT NULL AND expires_at <= ?",
        (now,),
    )
    cursor.execute("SELECT * FROM bot_bans ORDER BY created_at DESC")
    bot_bans = [dict(row) | {"source": "moderation"} for row in cursor.fetchall()]
    cursor.execute(
        """
        SELECT user_id, captcha_banned_until AS expires_at
        FROM users WHERE captcha_banned_until IS NOT NULL AND captcha_banned_until > ?
        ORDER BY captcha_banned_until DESC
        """,
        (now,),
    )
    captcha_bans = [
        {
            "user_id": row["user_id"], "moderator_id": None,
            "reason": "Failed Visual Anti-Bot Captcha", "created_at": None,
            "expires_at": row["expires_at"], "is_permanent": 0, "source": "captcha",
        }
        for row in cursor.fetchall()
    ]
    conn.commit()
    conn.close()
    return bot_bans + captcha_bans

def clear_all_captcha_state(user_id):
    get_user_data(user_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users SET
            is_captcha_active = 0, captcha_code = NULL, captcha_attempts = 0,
            captcha_regens = 0, captcha_banned_until = NULL,
            captcha_mine_actions = 0, captcha_mine_limit = ?
        WHERE user_id = ?
        """,
        (CAPTCHA_ACTION_INTERVAL, str(user_id)),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

def count_open_tickets(owner_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) AS amount FROM tickets WHERE owner_id = ? AND status = 'open'",
        (str(owner_id),),
    )
    amount = cursor.fetchone()["amount"]
    conn.close()
    return amount

def create_ticket_record(channel_id, guild_id, owner_id, ticket_type):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tickets (channel_id, guild_id, owner_id, ticket_type, created_at, status)
        VALUES (?, ?, ?, ?, ?, 'open')
        """,
        (str(channel_id), str(guild_id), str(owner_id), ticket_type, now),
    )
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

def get_open_ticket(channel_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM tickets WHERE channel_id = ? AND status = 'open'",
        (str(channel_id),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def close_ticket_record(channel_id, moderator_id, reason):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE tickets SET status = 'closed', closed_at = ?, closed_by = ?, close_reason = ?
        WHERE channel_id = ? AND status = 'open'
        """,
        (now, str(moderator_id), reason, str(channel_id)),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

def is_captcha_banned(status):
    banned_until = status.get("captcha_banned_until") if status else None
    if not banned_until:
        return False, None
    until = datetime.fromisoformat(banned_until)
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < until, until

def activate_captcha(user_id, code):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET is_captcha_active = 1,
            captcha_code = ?,
            captcha_attempts = 0,
            captcha_regens = 0,
            captcha_mine_actions = 0,
            captcha_mine_limit = ?
        WHERE user_id = ?
        """,
        (code, _new_captcha_limit(), str(user_id)),
    )
    conn.commit()
    conn.close()

def regenerate_captcha(user_id, code):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET captcha_code = ?,
            captcha_regens = captcha_regens + 1
        WHERE user_id = ?
        """,
        (code, str(user_id)),
    )
    conn.commit()
    conn.close()

def increment_captcha_attempts(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET captcha_attempts = captcha_attempts + 1 WHERE user_id = ?",
        (str(user_id),),
    )
    cursor.execute("SELECT captcha_attempts FROM users WHERE user_id = ?", (str(user_id),))
    attempts = cursor.fetchone()["captcha_attempts"]
    conn.commit()
    conn.close()
    return attempts

def ban_for_failed_captcha(user_id):
    banned_until = datetime.now(timezone.utc) + timedelta(days=CAPTCHA_BAN_DAYS)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET is_captcha_active = 1,
            captcha_code = NULL,
            captcha_banned_until = ?
        WHERE user_id = ?
        """,
        (banned_until.isoformat(), str(user_id)),
    )
    conn.commit()
    conn.close()
    return banned_until

def clear_captcha(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET is_captcha_active = 0,
            captcha_code = NULL,
            captcha_attempts = 0,
            captcha_regens = 0,
            captcha_banned_until = NULL,
            captcha_mine_actions = 0,
            captcha_mine_limit = ?
        WHERE user_id = ?
        """,
        (_new_captcha_limit(), str(user_id)),
    )
    conn.commit()
    conn.close()

def record_mine_for_captcha(user_id, code_factory):
    get_user_data(user_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT is_captcha_active, captcha_mine_actions, captcha_mine_limit FROM users WHERE user_id = ?",
        (str(user_id),),
    )
    row = cursor.fetchone()
    if not row or row["is_captcha_active"]:
        conn.close()
        return False, None

    actions = (row["captcha_mine_actions"] or 0) + 1
    if actions >= CAPTCHA_ACTION_INTERVAL:
        # One anti-bot check every 150 successful mine actions. A failed roll
        # starts a fresh 150-action interval instead of checking every click.
        if random.random() >= CAPTCHA_TRIGGER_CHANCE:
            cursor.execute(
                "UPDATE users SET captcha_mine_actions = 0, captcha_mine_limit = ? WHERE user_id = ?",
                (CAPTCHA_ACTION_INTERVAL, str(user_id)),
            )
            conn.commit()
            conn.close()
            return False, None
        code = code_factory()
        cursor.execute(
            """
            UPDATE users
            SET is_captcha_active = 1,
                captcha_code = ?,
                captcha_attempts = 0,
                captcha_regens = 0,
                captcha_mine_actions = 0,
                captcha_mine_limit = ?
            WHERE user_id = ?
            """,
            (code, CAPTCHA_ACTION_INTERVAL, str(user_id)),
        )
        conn.commit()
        conn.close()
        return True, code

    cursor.execute(
        """
        UPDATE users
        SET captcha_mine_actions = ?,
            captcha_mine_limit = ?
        WHERE user_id = ?
        """,
        (actions, CAPTCHA_ACTION_INTERVAL, str(user_id)),
    )
    conn.commit()
    conn.close()
    return False, None

def get_user_businesses(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT business_name FROM businesses WHERE user_id = ?", (str(user_id),))
    results = cursor.fetchall()
    conn.close()
    return [row[0] for row in results]

def add_business(user_id, business_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM businesses WHERE user_id = ? AND business_name = ?", (str(user_id), business_name))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO businesses (user_id, business_name) VALUES (?, ?)", (str(user_id), business_name))
        conn.commit()
    conn.close()

def get_current_week_start():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=now.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0).date().isoformat()

def get_clan_next_level_xp(level):
    if level >= CLAN_MAX_LEVEL:
        return None
    return level * 1000

def get_clan_ore_bonus_multiplier(user_id):
    clan = get_user_clan(user_id)
    if not clan:
        return 1
    return 1 + clan["level"] * 0.005

def get_user_clan(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.clan_id, c.name, c.tag, c.description, c.access, c.level, c.xp, c.total_xp,
               m.rank, m.total_xp AS member_total_xp
        FROM clan_members m
        JOIN clans c ON c.clan_id = m.clan_id
        WHERE m.user_id = ?
        """,
        (str(user_id),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_clan_by_name(name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clans WHERE name = ? COLLATE NOCASE", (name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_clan_by_id(clan_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clans WHERE clan_id = ?", (clan_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_clan_member_count(clan_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clan_members WHERE clan_id = ?", (clan_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_clan_members(clan_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, rank, joined_at, total_xp FROM clan_members WHERE clan_id = ? ORDER BY rank = 'Leader' DESC, total_xp DESC",
        (clan_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_clan_weekly_contributions(clan_id):
    week_start = get_current_week_start()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT user_id, xp FROM clan_weekly_xp
        WHERE clan_id = ? AND week_start = ?
        ORDER BY xp DESC
        """,
        (clan_id, week_start),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_clan(owner_id, name, tag):
    if get_user_clan(owner_id):
        return False, "already_in_clan", None
    if get_clan_by_name(name):
        return False, "name_taken", None

    user_data = get_user_data(owner_id)
    if user_data["wallet"] < CLAN_CREATE_COST:
        return False, "cash", None

    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO clans (name, tag, description, access, level, xp, total_xp, created_at)
        VALUES (?, ?, '', 'public', 1, 0, 0, ?)
        """,
        (name, tag, now),
    )
    clan_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO clan_members (clan_id, user_id, rank, joined_at, total_xp) VALUES (?, ?, 'Leader', ?, 0)",
        (clan_id, str(owner_id), now),
    )
    cursor.execute("UPDATE users SET wallet = wallet - ? WHERE user_id = ?", (CLAN_CREATE_COST, str(owner_id)))
    conn.commit()
    conn.close()
    return True, "ok", get_clan_by_id(clan_id)

def join_clan(user_id, name):
    if get_user_clan(user_id):
        return False, "already_in_clan", None

    clan = get_clan_by_name(name)
    if not clan:
        return False, "not_found", None

    if is_clan_banned(clan["clan_id"], user_id):
        return False, "banned", clan

    if get_clan_member_count(clan["clan_id"]) >= CLAN_MAX_MEMBERS:
        return False, "full", clan

    if clan["access"] == "invite":
        invite = get_active_clan_invite(user_id, clan["clan_id"])
        if not invite:
            return False, "invite_required", clan

    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clan_members (clan_id, user_id, rank, joined_at, total_xp) VALUES (?, ?, 'Member', ?, 0)",
        (clan["clan_id"], str(user_id), now),
    )
    cursor.execute("DELETE FROM clan_invites WHERE user_id = ?", (str(user_id),))
    conn.commit()
    conn.close()
    return True, "ok", clan

def leave_clan(user_id):
    clan = get_user_clan(user_id)
    if not clan:
        return False, "not_in_clan"
    if clan["rank"] == "Leader":
        return False, "leader"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clan_members WHERE user_id = ?", (str(user_id),))
    conn.commit()
    conn.close()
    return True, "ok"

def is_clan_banned(clan_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM clan_bans WHERE clan_id = ? AND user_id = ?",
        (clan_id, str(user_id)),
    )
    banned = cursor.fetchone() is not None
    conn.close()
    return banned

def ban_clan_member(leader_id, target_id):
    clan = get_user_clan(leader_id)
    if not clan:
        return False, "not_in_clan", None
    if clan["rank"] != "Leader":
        return False, "not_leader", clan
    if str(leader_id) == str(target_id):
        return False, "self", clan

    target_clan = get_user_clan(target_id)
    if not target_clan or target_clan["clan_id"] != clan["clan_id"]:
        return False, "target_not_member", clan

    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO clan_bans (clan_id, user_id, banned_by, created_at) VALUES (?, ?, ?, ?)",
        (clan["clan_id"], str(target_id), str(leader_id), now),
    )
    cursor.execute(
        "DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?",
        (clan["clan_id"], str(target_id)),
    )
    cursor.execute(
        "DELETE FROM clan_invites WHERE clan_id = ? AND user_id = ?",
        (clan["clan_id"], str(target_id)),
    )
    conn.commit()
    conn.close()
    return True, "ok", clan

def delete_clan(leader_id, expected_clan_id=None):
    clan = get_user_clan(leader_id)
    if not clan:
        return False, "not_in_clan", None
    if clan["rank"] != "Leader":
        return False, "not_leader", clan
    if expected_clan_id is not None and clan["clan_id"] != expected_clan_id:
        return False, "clan_changed", clan

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clans WHERE clan_id = ?", (clan["clan_id"],))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted, "ok" if deleted else "not_found", clan

def delete_clan_by_id(clan_id):
    clan = get_clan_by_id(clan_id)
    if not clan:
        return False, None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clans WHERE clan_id = ?", (clan_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted, clan

def admin_update_clan(clan_id, name=None, tag=None, description=None, access=None):
    clan = get_clan_by_id(clan_id)
    if not clan:
        return False, "not_found", None

    updates = []
    values = []
    if name is not None:
        existing = get_clan_by_name(name)
        if existing and existing["clan_id"] != clan_id:
            return False, "name_taken", clan
        updates.append("name = ?")
        values.append(name)
    if tag is not None:
        updates.append("tag = ?")
        values.append(tag)
    if description is not None:
        updates.append("description = ?")
        values.append(description)
    if access is not None:
        updates.append("access = ?")
        values.append(access)

    if not updates:
        return False, "nothing", clan

    values.append(clan_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE clans SET {', '.join(updates)} WHERE clan_id = ?", values)
    conn.commit()
    conn.close()
    return True, "ok", get_clan_by_id(clan_id)

def get_clan_tags(user_ids):
    normalized = [str(user_id) for user_id in user_ids]
    if not normalized:
        return {}
    placeholders = ",".join("?" for _ in normalized)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT m.user_id, c.tag
        FROM clan_members m
        JOIN clans c ON c.clan_id = m.clan_id
        WHERE m.user_id IN ({placeholders})
        """,
        normalized,
    )
    tags = {row["user_id"]: row["tag"] for row in cursor.fetchall()}
    conn.close()
    return tags

def transfer_clan_leadership(leader_id, target_id):
    clan = get_user_clan(leader_id)
    if not clan:
        return False, "not_in_clan"
    if clan["rank"] != "Leader":
        return False, "not_leader"
    if str(leader_id) == str(target_id):
        return False, "self"

    target_clan = get_user_clan(target_id)
    if not target_clan or target_clan["clan_id"] != clan["clan_id"]:
        return False, "target_not_member"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clan_members SET rank = 'Member' WHERE clan_id = ? AND user_id = ?",
        (clan["clan_id"], str(leader_id)),
    )
    cursor.execute(
        "UPDATE clan_members SET rank = 'Leader' WHERE clan_id = ? AND user_id = ?",
        (clan["clan_id"], str(target_id)),
    )
    conn.commit()
    conn.close()
    return True, "ok"

def update_clan_settings(user_id, tag=None, description=None, access=None):
    clan = get_user_clan(user_id)
    if not clan:
        return False, "not_in_clan", None
    if clan["rank"] != "Leader":
        return False, "not_leader", clan

    updates = []
    values = []
    if tag is not None:
        updates.append("tag = ?")
        values.append(tag)
    if description is not None:
        updates.append("description = ?")
        values.append(description)
    if access is not None:
        updates.append("access = ?")
        values.append(access)

    if not updates:
        return False, "nothing", clan

    values.append(clan["clan_id"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE clans SET {', '.join(updates)} WHERE clan_id = ?", values)
    conn.commit()
    conn.close()
    return True, "ok", get_clan_by_id(clan["clan_id"])

def create_clan_invite(inviter_id, target_id):
    clan = get_user_clan(inviter_id)
    if not clan:
        return False, "not_in_clan", None
    if get_user_clan(target_id):
        return False, "target_in_clan", clan
    if is_clan_banned(clan["clan_id"], target_id):
        return False, "target_banned", clan

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    expires_at = (now_dt + timedelta(seconds=CLAN_INVITE_SECONDS)).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO clan_invites (clan_id, user_id, inviter_id, created_at, notified_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(clan_id, user_id) DO UPDATE SET
            inviter_id = excluded.inviter_id,
            created_at = excluded.created_at,
            notified_at = excluded.notified_at,
            expires_at = excluded.expires_at
        """,
        (clan["clan_id"], str(target_id), str(inviter_id), now, now, expires_at),
    )
    conn.commit()
    conn.close()
    return True, "ok", clan

def get_active_clan_invite(user_id, clan_id=None):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    if clan_id is None:
        cursor.execute(
            """
            SELECT i.*, c.name, c.tag FROM clan_invites i
            JOIN clans c ON c.clan_id = i.clan_id
            WHERE i.user_id = ? AND i.expires_at IS NOT NULL AND i.expires_at > ?
            ORDER BY i.expires_at DESC LIMIT 1
            """,
            (str(user_id), now),
        )
    else:
        cursor.execute(
            """
            SELECT i.*, c.name, c.tag FROM clan_invites i
            JOIN clans c ON c.clan_id = i.clan_id
            WHERE i.user_id = ? AND i.clan_id = ? AND i.expires_at IS NOT NULL AND i.expires_at > ?
            """,
            (str(user_id), clan_id, now),
        )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def activate_pending_clan_invite(user_id):
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    expires_at = (now_dt + timedelta(seconds=CLAN_INVITE_SECONDS)).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT i.clan_id, c.name, c.tag
        FROM clan_invites i
        JOIN clans c ON c.clan_id = i.clan_id
        WHERE i.user_id = ? AND i.notified_at IS NULL
        ORDER BY i.created_at DESC LIMIT 1
        """,
        (str(user_id),),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    cursor.execute(
        "UPDATE clan_invites SET notified_at = ?, expires_at = ? WHERE clan_id = ? AND user_id = ?",
        (now, expires_at, row["clan_id"], str(user_id)),
    )
    conn.commit()
    conn.close()
    data = dict(row)
    data["expires_at"] = expires_at
    return data

def grant_clan_xp(user_id, xp):
    clan = get_user_clan(user_id)
    if not clan or xp <= 0:
        return None

    week_start = get_current_week_start()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clan_members SET total_xp = total_xp + ? WHERE clan_id = ? AND user_id = ?",
        (xp, clan["clan_id"], str(user_id)),
    )
    cursor.execute(
        """
        INSERT INTO clan_weekly_xp (clan_id, user_id, week_start, xp)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(clan_id, user_id, week_start) DO UPDATE SET xp = xp + excluded.xp
        """,
        (clan["clan_id"], str(user_id), week_start, xp),
    )

    level = clan["level"]
    current_xp = clan["xp"] + xp
    total_xp = clan["total_xp"] + xp
    leveled = 0
    while level < CLAN_MAX_LEVEL:
        needed = get_clan_next_level_xp(level)
        if current_xp < needed:
            break
        current_xp -= needed
        level += 1
        leveled += 1
    if level >= CLAN_MAX_LEVEL:
        level = CLAN_MAX_LEVEL
        current_xp = 0

    cursor.execute(
        "UPDATE clans SET level = ?, xp = ?, total_xp = ? WHERE clan_id = ?",
        (level, current_xp, total_xp, clan["clan_id"]),
    )
    conn.commit()
    conn.close()
    return {"clan_id": clan["clan_id"], "level": level, "xp": current_xp, "gained": xp, "leveled": leveled}

def get_clan_top(limit=10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT clan_id, name, tag, level, xp, total_xp
        FROM clans
        ORDER BY level DESC, total_xp DESC, xp DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_starting_capital_amount(user_data):
    level = user_data.get("prestige_capital_level", 0)
    amounts = PRESTIGE_UPGRADES["starting_capital"]["amounts"]
    if level <= 0:
        return 0
    return amounts[min(level, len(amounts)) - 1]

def get_prestige_income_multiplier(user_data):
    return 1 + user_data.get("prestige_manager_level", 0) * 0.20

def get_prestige_ore_value_multiplier(user_data):
    return 1 + user_data.get("prestige_ore_value_level", 0) * 0.20

def prestige_reset_user(user_id):
    user_data = get_user_data(user_id)
    new_prestige_level = user_data.get("prestige_level", 0) + 1
    starting_cash = get_starting_capital_amount(user_data)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (str(user_id), PRESTIGE_TOKEN_NAME),
    )
    row = cursor.fetchone()
    token_quantity = (row[0] if row else 0) + 1

    cursor.execute("DELETE FROM inventory WHERE user_id = ?", (str(user_id),))
    cursor.execute(
        "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
        (str(user_id), PRESTIGE_TOKEN_NAME, token_quantity),
    )
    cursor.execute("DELETE FROM businesses WHERE user_id = ?", (str(user_id),))
    cursor.execute("DELETE FROM daily_quests WHERE user_id = ?", (str(user_id),))
    cursor.execute("DELETE FROM active_boosts WHERE user_id = ?", (str(user_id),))
    cursor.execute(
        """
        UPDATE users
        SET wallet = ?,
            bank = 0,
            last_work = NULL,
            last_collect = NULL,
            last_mine = NULL,
            current_pickaxe = 'Stone Pickaxe',
            prestige_work_count = 0,
            time_management_level = 0,
            business_optimization_level = 0,
            miner_boost_level = 0,
            lapis = 0,
            prestige_level = ?,
            prestige_ready_notified = 0
        WHERE user_id = ?
        """,
        (starting_cash, new_prestige_level, str(user_id)),
    )
    conn.commit()
    conn.close()
    return new_prestige_level, token_quantity, starting_cash

def buy_prestige_upgrade(user_id, upgrade_id):
    if upgrade_id not in PRESTIGE_UPGRADE_COLUMNS:
        raise ValueError(f"Unknown prestige upgrade: {upgrade_id}")

    user_data = get_user_data(user_id)
    column = PRESTIGE_UPGRADE_COLUMNS[upgrade_id]
    current_level = user_data.get(column, 0)
    max_level = min(
        PRESTIGE_UPGRADES[upgrade_id]["max_level"],
        1 + user_data.get("prestige_level", 0) // 5,
    )
    if current_level >= max_level:
        return False, "maxed", current_level

    inventory = get_user_inventory(user_id)
    token_quantity = inventory.get(PRESTIGE_TOKEN_NAME, 0)
    if token_quantity < 1:
        return False, "currency", current_level

    inventory[PRESTIGE_TOKEN_NAME] = token_quantity - 1
    update_user_inventory(user_id, inventory)
    update_prestige_upgrade_level(user_id, upgrade_id, current_level + 1)
    return True, "ok", current_level + 1

def can_work(user_id):
    data = get_user_data(user_id)
    last_work_str = data.get("last_work")
    if not last_work_str:
        return True, None
    
    last_work = datetime.fromisoformat(last_work_str)
    if last_work.tzinfo is None:
        last_work = last_work.replace(tzinfo=timezone.utc)
    
    # Apply upgrade Time Management
    time_management_level = data.get("time_management_level", 0)
    work_reduction_minutes = 0
    if time_management_level > 0:
        levels = UPGRADES["time_management"]["levels"]
        for i in range(time_management_level):
            work_reduction_minutes += levels[i]["work_reduction_minutes"]
    
    if "work_rush" in get_active_boosts(user_id):
        reduced_cooldown = timedelta(seconds=5)
    else:
        base_cooldown = timedelta(hours=2)
        reduced_cooldown = base_cooldown - timedelta(minutes=work_reduction_minutes)
        reduced_cooldown *= _seasonal_cooldown_multiplier("work")
    next_work = last_work + reduced_cooldown
    
    if datetime.now(timezone.utc) >= next_work:
        return True, None
    return False, next_work

def can_collect(user_id):
    data = get_user_data(user_id)
    last_collect_str = data.get("last_collect")
    if not last_collect_str:
        return True, None
    last_collect = datetime.fromisoformat(last_collect_str)
    if last_collect.tzinfo is None:
        last_collect = last_collect.replace(tzinfo=timezone.utc)
    next_collect = last_collect + timedelta(hours=6) * _seasonal_cooldown_multiplier("collect")
    if datetime.now(timezone.utc) >= next_collect:
        return True, None
    return False, next_collect

def can_mine(user_id):
    data = get_user_data(user_id)
    final_cooldown = get_mine_cooldown(user_id, data)
    last_mine_str = data.get("last_mine")
    if not last_mine_str:
        return True, None, final_cooldown
    
    last_mine = datetime.fromisoformat(last_mine_str)
    if last_mine.tzinfo is None:
        last_mine = last_mine.replace(tzinfo=timezone.utc)
    
    next_mine = last_mine + timedelta(seconds=final_cooldown)
    if datetime.now(timezone.utc) >= next_mine:
        return True, None, final_cooldown
    return False, next_mine, final_cooldown

def get_mine_cooldown(user_id, data=None):
    data = data or get_user_data(user_id)
    pickaxe_name = data.get("current_pickaxe", "Stone Pickaxe")
    pickaxe_delay = PICKAXES.get(pickaxe_name, {}).get("cooldown_add", PICKAXE_COOLDOWN_ADD)
    time_management_level = data.get("time_management_level", 0)
    levels = UPGRADES["time_management"]["levels"][:time_management_level]
    mine_reduction = sum(level["mine_reduction"] for level in levels)
    final_cooldown = BASE_MINE_COOLDOWN + pickaxe_delay - mine_reduction
    if "mine_haste" in get_active_boosts(user_id):
        final_cooldown *= 0.65
    final_cooldown *= _seasonal_cooldown_multiplier("mine")
    return max(MIN_MINE_COOLDOWN, final_cooldown)


def _seasonal_cooldown_multiplier(action):
    raw_state = get_bot_state("current_seasonal_event")
    if not raw_state:
        return 1.0
    try:
        state = json.loads(raw_state)
        expires_at = datetime.fromisoformat(state["expires_at"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return 1.0
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= expires_at:
        return 1.0
    multipliers = {
        "mine": {"swift_pickaxes": 0.70, "production_sprint": 0.70},
        "work": {"quick_shift": 0.65, "worker_festival": 0.65},
        "collect": {"fast_collections": 0.65, "business_festival": 0.65},
    }
    return multipliers.get(action, {}).get(state.get("event_id"), 1.0)

def get_global_top():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, wallet as total FROM users WHERE wallet > 0 ORDER BY wallet DESC")
    results = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in results]

def get_server_top(guild):
    guild_members = [str(member.id) for member in guild.members if not member.bot]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, wallet as total FROM users WHERE wallet > 0 ORDER BY wallet DESC")
    results = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in results if row[0] in guild_members]

def get_mine_result(pickaxe_name, user_id=None):
    pickaxe = PICKAXES[pickaxe_name]
    available_ores = pickaxe["ores"]
    
    results = {}
    weights = [ORES[name]["chance"] for name in available_ores]
    rolls = random.randint(pickaxe.get("rolls_min", 1), pickaxe.get("rolls_max", 1))
    user_data = get_user_data(user_id) if user_id is not None else {}
    double_chance = user_data.get("prestige_double_ore_level", 0) * 8
    mining_frenzy = user_id is not None and "mining_frenzy" in get_active_boosts(user_id)
    for _ in range(rolls):
        selected_ore = random.choices(available_ores, weights=weights, k=1)[0]
        amount = random.randint(pickaxe["amount_min"], pickaxe["amount_max"])
        if double_chance > 0 and random.random() * 100 < double_chance:
            amount *= 2
        if mining_frenzy:
            amount = max(1, round(amount * 1.5))
        results[selected_ore] = results.get(selected_ore, 0) + amount
    return results




def transfer_user_progress(source_user_id, target_user_id):
    source_user_id = str(source_user_id)
    target_user_id = str(target_user_id)

    if source_user_id == target_user_id:
        return False, "same_user", None

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (source_user_id,))
        source = cursor.fetchone()

        if not source:
            return False, "source_not_found", None

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (target_user_id,))
        target = cursor.fetchone()

        if not target:
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute(
                """
                INSERT INTO users (
                    user_id,
                    registered_at,
                    current_pickaxe,
                    time_management_level,
                    business_optimization_level,
                    miner_boost_level,
                    prestige_level,
                    prestige_manager_level,
                    prestige_capital_level,
                    prestige_double_ore_level,
                    prestige_ore_value_level
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    target_user_id,
                    now,
                    "Stone Pickaxe",
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ),
            )

            cursor.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (target_user_id,),
            )

            target = cursor.fetchone()

        source_clan = cursor.execute(
            "SELECT clan_id, rank FROM clan_members WHERE user_id = ?",
            (source_user_id,),
        ).fetchone()

        target_clan = cursor.execute(
            "SELECT clan_id, rank FROM clan_members WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()

        if target_clan:
            return False, "target_in_clan", None

        source_open_tickets = cursor.execute(
            "SELECT COUNT(*) AS amount FROM tickets WHERE owner_id = ? AND status = 'open'",
            (source_user_id,),
        ).fetchone()["amount"]

        if source_open_tickets:
            return False, "source_has_ticket", source_open_tickets

        transferable_tables = (
            "businesses",
            "inventory",
            "clan_members",
            "clan_weekly_xp",
            "clan_invites",
            "clan_bans",
            "daily_quests",
            "active_boosts",
        )

        target_progress = {
            "businesses": cursor.execute(
                "SELECT COUNT(*) AS amount FROM businesses WHERE user_id = ?",
                (target_user_id,),
            ).fetchone()["amount"],
            "inventory": cursor.execute(
                "SELECT COUNT(*) AS amount FROM inventory WHERE user_id = ?",
                (target_user_id,),
            ).fetchone()["amount"],
            "daily_quests": cursor.execute(
                "SELECT COUNT(*) AS amount FROM daily_quests WHERE user_id = ?",
                (target_user_id,),
            ).fetchone()["amount"],
            "active_boosts": cursor.execute(
                "SELECT COUNT(*) AS amount FROM active_boosts WHERE user_id = ?",
                (target_user_id,),
            ).fetchone()["amount"],
            "clan_invites": cursor.execute(
                "SELECT COUNT(*) AS amount FROM clan_invites WHERE user_id = ?",
                (target_user_id,),
            ).fetchone()["amount"],
            "clan_bans": cursor.execute(
                "SELECT COUNT(*) AS amount FROM clan_bans WHERE user_id = ?",
                (target_user_id,),
            ).fetchone()["amount"],
            "clan_weekly_xp": cursor.execute(
                "SELECT COUNT(*) AS amount FROM clan_weekly_xp WHERE user_id = ?",
                (target_user_id,),
            ).fetchone()["amount"],
        }

        if any(target_progress.values()):
            return False, "target_has_progress", target_progress

        source_values = dict(source)

        source_values["user_id"] = target_user_id
        source_values["is_captcha_active"] = 0
        source_values["captcha_code"] = None
        source_values["captcha_attempts"] = 0
        source_values["captcha_regens"] = 0
        source_values["captcha_banned_until"] = None
        source_values["captcha_mine_actions"] = 0
        source_values["captcha_mine_limit"] = CAPTCHA_ACTION_INTERVAL

        columns = list(source.keys())
        columns.remove("user_id")

        set_clause = ", ".join(
            f"{column} = ?" for column in columns
        )

        values = [
            source_values[column]
            for column in columns
        ]

        values.append(target_user_id)

        cursor.execute(
            f"UPDATE users SET {set_clause} WHERE user_id = ?",
            values,
        )

        for table in transferable_tables:
            cursor.execute(
                f"DELETE FROM {table} WHERE user_id = ?",
                (target_user_id,),
            )

        for table in transferable_tables:
            cursor.execute(
                f"SELECT * FROM {table} WHERE user_id = ?",
                (source_user_id,),
            )

            rows = cursor.fetchall()

            if not rows:
                continue

            table_columns = [
                column["name"]
                for column in cursor.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            ]

            placeholders = ", ".join("?" for _ in table_columns)
            column_sql = ", ".join(table_columns)

            for row in rows:
                values = []

                for column in table_columns:
                    value = row[column]

                    if column == "user_id":
                        value = target_user_id

                    values.append(value)

                cursor.execute(
                    f"""
                    INSERT INTO {table} ({column_sql})
                    VALUES ({placeholders})
                    """,
                    values,
                )

        for table in transferable_tables:
            cursor.execute(
                f"DELETE FROM {table} WHERE user_id = ?",
                (source_user_id,),
            )

        cursor.execute(
            "DELETE FROM users WHERE user_id = ?",
            (source_user_id,),
        )

        conn.commit()

        return True, "success", {
            "source_user_id": source_user_id,
            "target_user_id": target_user_id,
            "wallet": source["wallet"],
            "bank": source["bank"],
            "lapis": source["lapis"],
            "prestige_level": source["prestige_level"],
            "current_pickaxe": source["current_pickaxe"],
            "clan_id": source_clan["clan_id"] if source_clan else None,
            "clan_rank": source_clan["rank"] if source_clan else None,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()