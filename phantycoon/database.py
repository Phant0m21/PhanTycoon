import random
import sqlite3
from datetime import datetime, timedelta, timezone

from phantycoon.config import DB_FILE
from phantycoon.data import ORES, PICKAXES, UPGRADES

STAT_COLUMNS = {
    "total_earned",
    "total_spent",
    "work_earned",
    "collect_earned",
    "work_count",
    "games_played",
}

UPGRADE_COLUMNS = {
    "time_management_level",
    "business_optimization_level",
    "miner_boost_level",
}


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица пользователей
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
            games_played INTEGER DEFAULT 0,
            current_pickaxe TEXT DEFAULT 'Каменная кирка',
            time_management_level INTEGER DEFAULT 0,
            business_optimization_level INTEGER DEFAULT 0,
            miner_boost_level INTEGER DEFAULT 0
        )
    """)
    
    # Таблица бизнесов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            user_id TEXT,
            business_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # Таблица инвентаря
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id TEXT,
            item_name TEXT,
            quantity INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
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
        "games_played": "INTEGER DEFAULT 0",
        "current_pickaxe": "TEXT DEFAULT 'Каменная кирка'",
        "time_management_level": "INTEGER DEFAULT 0",
        "business_optimization_level": "INTEGER DEFAULT 0",
        "miner_boost_level": "INTEGER DEFAULT 0",
    }
    for column, definition in required_columns.items():
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_businesses_user_id ON businesses(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id)")
    
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT wallet, bank, last_work, last_collect, last_mine, registered_at, 
               total_earned, total_spent, work_earned, collect_earned, 
               work_count, games_played, current_pickaxe,
               time_management_level, business_optimization_level, miner_boost_level
        FROM users WHERE user_id = ?
    """, (str(user_id),))
    result = cursor.fetchone()
    
    if not result:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO users (user_id, registered_at, current_pickaxe,
                time_management_level, business_optimization_level, miner_boost_level) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(user_id), now, "Каменная кирка", 0, 0, 0))
        conn.commit()
        conn.close()
        return {
            "wallet": 0, "bank": 0, "last_work": None, "last_collect": None, "last_mine": None,
            "registered_at": now, "total_earned": 0, "total_spent": 0,
            "work_earned": 0, "collect_earned": 0, "work_count": 0, "games_played": 0,
            "current_pickaxe": "Каменная кирка",
            "time_management_level": 0,
            "business_optimization_level": 0,
            "miner_boost_level": 0
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
        "games_played": result[11] if result[11] is not None else 0,
        "current_pickaxe": result[12] if result[12] is not None else "Каменная кирка",
        "time_management_level": result[13] if result[13] is not None else 0,
        "business_optimization_level": result[14] if result[14] is not None else 0,
        "miner_boost_level": result[15] if result[15] is not None else 0
    }

def update_user_wallet(user_id, new_wallet):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (new_wallet, str(user_id)))
    conn.commit()
    conn.close()

def update_user_bank(user_id, new_bank):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET bank = ? WHERE user_id = ?", (new_bank, str(user_id)))
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

def update_current_pickaxe(user_id, pickaxe_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_pickaxe = ? WHERE user_id = ?", (pickaxe_name, str(user_id)))
    conn.commit()
    conn.close()

def update_upgrade_level(user_id, upgrade_name, level):
    if upgrade_name not in UPGRADE_COLUMNS:
        raise ValueError(f"Unknown upgrade column: {upgrade_name}")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {upgrade_name} = ? WHERE user_id = ?", (level, str(user_id)))
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

def can_work(user_id):
    data = get_user_data(user_id)
    last_work_str = data.get("last_work")
    if not last_work_str:
        return True, None
    
    last_work = datetime.fromisoformat(last_work_str)
    if last_work.tzinfo is None:
        last_work = last_work.replace(tzinfo=timezone.utc)
    
    # Учитываем апгрейд Менеджмент времени
    time_management_level = data.get("time_management_level", 0)
    work_reduction_minutes = 0
    if time_management_level > 0:
        levels = UPGRADES["time_management"]["levels"]
        for i in range(time_management_level):
            work_reduction_minutes += levels[i]["work_reduction_minutes"]
    
    base_cooldown = timedelta(hours=2)
    reduced_cooldown = base_cooldown - timedelta(minutes=work_reduction_minutes)
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
    next_collect = last_collect + timedelta(hours=6)
    if datetime.now(timezone.utc) >= next_collect:
        return True, None
    return False, next_collect

def can_mine(user_id):
    data = get_user_data(user_id)
    last_mine_str = data.get("last_mine")
    if not last_mine_str:
        return True, None, 0
    
    last_mine = datetime.fromisoformat(last_mine_str)
    if last_mine.tzinfo is None:
        last_mine = last_mine.replace(tzinfo=timezone.utc)
    
    pickaxe_name = data.get("current_pickaxe", "Каменная кирка")
    base_cooldown = PICKAXES.get(pickaxe_name, {}).get("cooldown", 4.2)
    
    # Учитываем апгрейд Менеджмент времени
    time_management_level = data.get("time_management_level", 0)
    mine_reduction = 0
    if time_management_level > 0:
        levels = UPGRADES["time_management"]["levels"]
        for i in range(time_management_level):
            mine_reduction += levels[i]["mine_reduction"]
    
    final_cooldown = max(0.5, base_cooldown - mine_reduction)
    next_mine = last_mine + timedelta(seconds=final_cooldown)
    
    if datetime.now(timezone.utc) >= next_mine:
        return True, None, final_cooldown
    return False, next_mine, final_cooldown

def get_global_top():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, wallet + bank as total FROM users WHERE wallet + bank > 0 ORDER BY total DESC")
    results = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in results]

def get_server_top(guild):
    guild_members = [str(member.id) for member in guild.members if not member.bot]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, wallet + bank as total FROM users WHERE wallet + bank > 0 ORDER BY total DESC")
    results = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in results if row[0] in guild_members]

def get_mine_result(pickaxe_name):
    pickaxe = PICKAXES[pickaxe_name]
    available_ores = pickaxe["ores"]
    
    # Выбираем руду на основе шансов
    roll = random.random() * 100
    cumulative = 0
    selected_ore = None
    
    for ore_name, ore_data in ORES.items():
        if ore_name not in available_ores:
            continue
        cumulative += ore_data["chance"]
        if roll <= cumulative:
            selected_ore = ore_name
            break
    
    if selected_ore is None:
        selected_ore = available_ores[-1] if available_ores else "Уголь"
    
    # Количество руды
    amount = random.randint(pickaxe["amount_min"], pickaxe["amount_max"])
    
    return selected_ore, amount
