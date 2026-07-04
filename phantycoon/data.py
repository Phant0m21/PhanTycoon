# Данные о кирках
PICKAXES = {
    "Каменная кирка": {
        "emoji": "<:stonepickaxe:1522995642996228106>",
        "cooldown": 4.2,
        "amount_min": 1,
        "amount_max": 1,
        "ores": ["Уголь", "Медь"],
        "default": True,
        "price": 0
    },
    "Железная кирка": {
        "emoji": "<:ironpickaxe:1522995651095298129>",
        "cooldown": 3.8,
        "amount_min": 1,
        "amount_max": 2,
        "ores": ["Уголь", "Медь", "Железо"],
        "default": False,
        "price": 15000
    },
    "Золотая кирка": {
        "emoji": "<:goldenpickaxe:1522995649828618292>",
        "cooldown": 3.5,
        "amount_min": 1,
        "amount_max": 3,
        "ores": ["Уголь", "Медь", "Железо", "Золото"],
        "default": False,
        "price": 75000
    },
    "Алмазная кирка": {
        "emoji": "<:diamondpickaxe:1522995648511868928>",
        "cooldown": 3.1,
        "amount_min": 2,
        "amount_max": 4,
        "ores": ["Уголь", "Медь", "Железо", "Золото", "Алмаз"],
        "default": False,
        "price": 350000
    },
    "Незеритовая кирка": {
        "emoji": "<:netheritepickaxe:1522995647073226843>",
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
        "emoji": "<:coalore:1522995644506046524>",
        "chance": 60,
        "price_min": 5,
        "price_max": 7
    },
    "Медь": {
        "emoji": "<:copperore:1522995656967586013>",
        "chance": 24,
        "price_min": 15,
        "price_max": 17
    },
    "Железо": {
        "emoji": "<:ironore:1522995655440863482>",
        "chance": 12,
        "price_min": 32,
        "price_max": 37
    },
    "Золото": {
        "emoji": "<:goldore:1522995653750558810>",
        "chance": 3.7,
        "price_min": 72,
        "price_max": 83
    },
    "Алмаз": {
        "emoji": "<:diamond:1522995645877846027>",
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

