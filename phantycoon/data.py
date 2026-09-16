# Mining cooldown is independent of pickaxe tier. Every equipped pickaxe adds
# the same delay, and no combination of reductions can take it below the floor.
BASE_MINE_COOLDOWN = 3.1
PICKAXE_COOLDOWN_ADD = 1.1
MIN_MINE_COOLDOWN = 2.0

# Pickaxe data
PICKAXES = {
    "Stone Pickaxe": {
        "emoji": "<:stonepickaxe:1548925916305162270>",
        "cooldown_add": PICKAXE_COOLDOWN_ADD,
        "amount_min": 1,
        "amount_max": 2,
        "rolls_min": 2, "rolls_max": 2,
        "ores": ["Coal", "Copper"],
        "default": True,
        "price": 0
    },
    "Iron Pickaxe": {
        "emoji": "<:ironpickaxe:1548925917915512873>",
        "cooldown_add": PICKAXE_COOLDOWN_ADD,
        "amount_min": 1,
        "amount_max": 2,
        "ores": ["Coal", "Copper", "Iron"],
        "default": False,
        "price": 6000, "rolls_min": 2, "rolls_max": 3
    },
    "Golden Pickaxe": {
        "emoji": "<:goldpickaxe:1548925919060557894>",
        "cooldown_add": PICKAXE_COOLDOWN_ADD,
        "amount_min": 1,
        "amount_max": 3,
        "ores": ["Coal", "Copper", "Iron", "Gold"],
        "default": False,
        "price": 25000, "rolls_min": 3, "rolls_max": 4
    },
    "Diamond Pickaxe": {
        "emoji": "<:diamondpickaxe:1548925920579158147>",
        "cooldown_add": PICKAXE_COOLDOWN_ADD,
        "amount_min": 2,
        "amount_max": 4,
        "ores": ["Coal", "Copper", "Iron", "Gold", "Diamond"],
        "default": False,
        "price": 100000, "rolls_min": 4, "rolls_max": 5
    },
    "Netherite Pickaxe": {
        "emoji": "<:netheritepickaxe:1548925921870876682>",
        "cooldown_add": PICKAXE_COOLDOWN_ADD,
        "amount_min": 3,
        "amount_max": 5,
        "ores": ["Coal", "Copper", "Iron", "Gold", "Diamond"],
        "default": False,
        "price": 400000, "rolls_min": 5, "rolls_max": 7
    }
}

ORES = {
    "Coal": {
        "emoji": "<:coal:1548925287834591232>",
        "chance": 60,
        "price_min": 5,
        "price_max": 7
    },
    "Copper": {
        "emoji": "<:copper:1548925289541668884>",
        "chance": 24,
        "price_min": 15,
        "price_max": 17
    },
    "Iron": {
        "emoji": "<:iron:1548925291269988382>",
        "chance": 12,
        "price_min": 32,
        "price_max": 37
    },
    "Gold": {
        "emoji": "<:gold:1548925293576593408>",
        "chance": 3.7,
        "price_min": 72,
        "price_max": 83
    },
    "Diamond": {
        "emoji": "<:diamond:1548925294742605875>",
        "chance": 0.3,
        "price_min": 250,
        "price_max": 310
    }
}

PRESTIGE_TOKEN_NAME = "Ender Eye"
PRESTIGE_TOKEN_EMOJI = "<:prestigetoken:1548925568454492190>"
LAPIS_EMOJI = "<:lapislazuli:1548925566949003324>"

PRESTIGE_UPGRADES = {
    "commanding_manager": {
        "name": "Commanding Manager",
        "max_level": 5,
        "description": "Permanently increases /work and /collect income by +20% per level.",
    },
    "starting_capital": {
        "name": "Starting Capital",
        "max_level": 4,
        "description": "Grants extra cash after future prestige resets.",
        "amounts": [10000, 25000, 50000, 100000],
    },
    "double_vein": {
        "name": "Double Vein",
        "max_level": 5,
        "description": "Adds +8% chance per level to receive x2 ore when mining.",
    },
    "diamond_rush": {
        "name": "Diamond Rush",
        "max_level": 5,
        "description": "Permanently increases all ore sale prices by +20% per level.",
    },
}

# ==================== UPGRADE DATA ====================

UPGRADES = {
    "time_management": {
        "name": "Time Management",
        "emoji": "⏱️",
        "max_level": 8,
        "levels": [
            {"price": 2000, "mine_reduction": 0.3, "work_reduction_minutes": 10},
            {"price": 6000, "mine_reduction": 0.3, "work_reduction_minutes": 20},
            {"price": 15000, "mine_reduction": 0.3, "work_reduction_minutes": 30},
            {"price": 50000, "mine_reduction": 0.2, "work_reduction_minutes": 10},
            {"price": 80000, "mine_reduction": 0.2, "work_reduction_minutes": 10},
            {"price": 120000, "mine_reduction": 0.2, "work_reduction_minutes": 10},
            {"price": 180000, "mine_reduction": 0.2, "work_reduction_minutes": 10},
            {"price": 250000, "mine_reduction": 0.2, "work_reduction_minutes": 10}
        ]
    },
    "business_optimization": {
        "name": "Business Optimization",
        "emoji": "🏢",
        "max_level": 10,
        "levels": [
            {"price": 4000, "income_bonus": 10},
            {"price": 10000, "income_bonus": 10},
            {"price": 25000, "income_bonus": 10},
            {"price": 60000, "income_bonus": 10},
            {"price": 180000, "income_bonus": 10},
            {"price": 260000, "income_bonus": 10},
            {"price": 380000, "income_bonus": 10},
            {"price": 550000, "income_bonus": 10},
            {"price": 800000, "income_bonus": 10},
            {"price": 1100000, "income_bonus": 10}
        ]
    },
    "miner_boost": {
        "name": "Ore Miner",
        "emoji": "⛏️",
        "max_level": 12,
        "levels": [
            {"price": 1500, "ore_bonus": 5},
            {"price": 5000, "ore_bonus": 5},
            {"price": 12000, "ore_bonus": 5},
            {"price": 30000, "ore_bonus": 5},
            {"price": 75000, "ore_bonus": 5},
            {"price": 100000, "ore_bonus": 5},
            {"price": 150000, "ore_bonus": 5},
            {"price": 220000, "ore_bonus": 5},
            {"price": 320000, "ore_bonus": 5},
            {"price": 460000, "ore_bonus": 5},
            {"price": 650000, "ore_bonus": 5},
            {"price": 900000, "ore_bonus": 5}
        ]
    }
}
