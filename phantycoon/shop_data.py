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
            "pickaxes": {
                "Iron Pickaxe": {"price": 6000, "emoji": "<:ironpickaxe:1522995651095298129>", "category": "pickaxes"},
                "Golden Pickaxe": {"price": 25000, "emoji": "<:goldenpickaxe:1522995649828618292>", "category": "pickaxes"},
                "Diamond Pickaxe": {"price": 100000, "emoji": "<:diamondpickaxe:1522995648511868928>", "category": "pickaxes"},
                "Netherite Pickaxe": {"price": 400000, "emoji": "<:netheritepickaxe:1522995647073226843>", "category": "pickaxes"},
                "Iridium Pickaxe": {"price": 2500000, "emoji": "<:iridiumpickaxe:1549726709119713350>", "category": "pickaxes", "prestige_required": 5}
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
