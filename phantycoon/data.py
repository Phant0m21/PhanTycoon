# Данные о кирках
PICKAXES = {
    "Каменная кирка": {
        "emoji": "<:stonepickaxe:1521830845340455072>",
        "cooldown": 4.2,
        "amount_min": 1,
        "amount_max": 1,
        "ores": ["Уголь", "Медь"],
        "default": True,
        "price": 0
    },
    "Железная кирка": {
        "emoji": "<:ironpickaxe:1521827763022073916>",
        "cooldown": 3.8,
        "amount_min": 1,
        "amount_max": 2,
        "ores": ["Уголь", "Медь", "Железо"],
        "default": False,
        "price": 15000
    },
    "Золотая кирка": {
        "emoji": "<:goldenpickaxe:1521827761814110269>",
        "cooldown": 3.5,
        "amount_min": 1,
        "amount_max": 3,
        "ores": ["Уголь", "Медь", "Железо", "Золото"],
        "default": False,
        "price": 75000
    },
    "Алмазная кирка": {
        "emoji": "<:diamondpickaxe:1521827760647966800>",
        "cooldown": 3.1,
        "amount_min": 2,
        "amount_max": 4,
        "ores": ["Уголь", "Медь", "Железо", "Золото", "Алмаз"],
        "default": False,
        "price": 350000
    },
    "Незеритовая кирка": {
        "emoji": "<:netheritepickaxe:1521827759465431172>",
        "cooldown": 2.6,
        "amount_min": 3,
        "amount_max": 5,
        "ores": ["Уголь", "Медь", "Железо", "Золото", "Алмаз"],
        "default": False,
        "price": 1500000
    }
}

ORES = {
    "Уголь": {
        "emoji": "<:coalore:1521827756680286208>",
        "chance": 60,
        "price_min": 5,
        "price_max": 7
    },
    "Медь": {
        "emoji": "<:copperore:1521827769137234010>",
        "chance": 24,
        "price_min": 15,
        "price_max": 17
    },
    "Железо": {
        "emoji": "<:ironore:1521827767308783638>",
        "chance": 12,
        "price_min": 32,
        "price_max": 37
    },
    "Золото": {
        "emoji": "<:goldore:1521827765983252612>",
        "chance": 3.7,
        "price_min": 72,
        "price_max": 83
    },
    "Алмаз": {
        "emoji": "<:diamond:1521827757959413821>",
        "chance": 0.3,
        "price_min": 250,
        "price_max": 310
    }
}

# ==================== ДАННЫЕ АПГРЕЙДОВ ====================

UPGRADES = {
    "time_management": {
        "name": "Менеджмент времени",
        "emoji": "⏱️",
        "max_level": 3,
        "levels": [
            {"price": 5000, "mine_reduction": 0.3, "work_reduction_minutes": 10},
            {"price": 15000, "mine_reduction": 0.3, "work_reduction_minutes": 20},
            {"price": 30000, "mine_reduction": 0.3, "work_reduction_minutes": 30}
        ]
    },
    "business_optimization": {
        "name": "Оптимизация бизнесов",
        "emoji": "🏢",
        "max_level": 5,
        "levels": [
            {"price": 15000, "income_bonus": 10},
            {"price": 25000, "income_bonus": 10},
            {"price": 50000, "income_bonus": 10},
            {"price": 100000, "income_bonus": 10},
            {"price": 250000, "income_bonus": 10}
        ]
    },
    "miner_boost": {
        "name": "Майнер руды",
        "emoji": "⛏️",
        "max_level": 6,
        "levels": [
            {"price": 5000, "ore_bonus": 5},
            {"price": 15000, "ore_bonus": 5},
            {"price": 25000, "ore_bonus": 5},
            {"price": 50000, "ore_bonus": 5},
            {"price": 75000, "ore_bonus": 5},
            {"price": 120000, "ore_bonus": 5}
        ]
    }
}

