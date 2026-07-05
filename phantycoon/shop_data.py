import json

from phantycoon.config import SHOP_FILE


def load_shop():
    if not SHOP_FILE.exists():
        default_shop = {
            "business": {
                "Shawarma Stand": {"price": 1500, "income": 60, "emoji": "🌯", "category": "business"},
                "Car Wash": {"price": 6000, "income": 260, "emoji": "🚗", "category": "business"},
                "Gaming Cafe": {"price": 20000, "income": 1000, "emoji": "🎮", "category": "business"},
                "Nightclub": {"price": 50000, "income": 2800, "emoji": "💃", "category": "business"},
                "Casino": {"price": 150000, "income": 9000, "emoji": "🎰", "category": "business"}
            },
            "consumables": {
                "Energy Drink": {"price": 500, "effect": "reset_work", "emoji": "🥤", "category": "consumables", "description": "Resets the /work cooldown"},
                "Vitamins": {"price": 900, "effect": "work_boost", "emoji": "💊", "category": "consumables", "description": "Your next 3 work shifts pay +45%"},
                "Insurance": {"price": 2500, "effect": "insurance", "emoji": "📋", "category": "consumables", "description": "Protects you from minigame losses"}
            },
            "pickaxes": {
                "Iron Pickaxe": {"price": 15000, "emoji": "<:ironpickaxe:1522995651095298129>", "category": "pickaxes"},
                "Golden Pickaxe": {"price": 75000, "emoji": "<:goldenpickaxe:1522995649828618292>", "category": "pickaxes"},
                "Diamond Pickaxe": {"price": 350000, "emoji": "<:diamondpickaxe:1522995648511868928>", "category": "pickaxes"},
                "Netherite Pickaxe": {"price": 1500000, "emoji": "<:netheritepickaxe:1522995647073226843>", "category": "pickaxes"}
            },
            "other": {
                "Golden Crown": {"price": 1000000, "emoji": "👑", "category": "other", "description": "Profile flex cosmetic"},
                "Private Jet": {"price": 10000000, "emoji": "🛩️", "category": "other", "description": "Profile flex cosmetic"}
            }
        }
        with open(SHOP_FILE, "w", encoding="utf-8") as f:
            json.dump(default_shop, f, indent=4, ensure_ascii=False)
        return default_shop
    with open(SHOP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_shop(data):
    with open(SHOP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
