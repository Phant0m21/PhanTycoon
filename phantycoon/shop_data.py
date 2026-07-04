import json

from phantycoon.config import SHOP_FILE


def load_shop():
    if not SHOP_FILE.exists():
        default_shop = {
            "business": {
                "Шаурмичная": {"price": 1500, "income": 60, "emoji": "🌯", "category": "business"},
                "Автомойка": {"price": 6000, "income": 260, "emoji": "🚗", "category": "business"},
                "Компьютерный клуб": {"price": 20000, "income": 1000, "emoji": "🎮", "category": "business"},
                "Ночной клуб": {"price": 50000, "income": 2800, "emoji": "💃", "category": "business"},
                "Казино": {"price": 150000, "income": 9000, "emoji": "🎰", "category": "business"}
            },
            "consumables": {
                "Энергетик": {"price": 500, "effect": "reset_work", "emoji": "🥤", "category": "consumables", "description": "Сбрасывает кулдаун /work"},
                "Витамины": {"price": 900, "effect": "work_boost", "emoji": "💊", "category": "consumables", "description": "Следующие 3 работы дают 45% к заработку"},
                "Страховка": {"price": 2500, "effect": "insurance", "emoji": "📋", "category": "consumables", "description": "Защищает от неудач в играх"}
            },
            "pickaxes": {
                "Железная кирка": {"price": 15000, "emoji": "<:ironpickaxe:1521827763022073916>", "category": "pickaxes"},
                "Золотая кирка": {"price": 75000, "emoji": "<:goldenpickaxe:1521827761814110269>", "category": "pickaxes"},
                "Алмазная кирка": {"price": 350000, "emoji": "<:diamondpickaxe:1521827760647966800>", "category": "pickaxes"},
                "Незеритовая кирка": {"price": 1500000, "emoji": "<:netheritepickaxe:1521827759465431172>", "category": "pickaxes"}
            },
            "other": {
                "Золотая Корона": {"price": 1000000, "emoji": "👑", "category": "other", "description": "Визуальное дополнение"},
                "Личный Джет": {"price": 10000000, "emoji": "🛩️", "category": "other", "description": "Визуальное дополнение"}
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
