import disnake

from phantycoon.bot import bot
from phantycoon.cogs.help import HelpView
from phantycoon.cogs.clan import ClanView
from phantycoon.cogs.inventory import InventorySelect
from phantycoon.cogs.prestige import PrestigeShopView
from phantycoon.cogs.profile import ProfileView
from phantycoon.cogs.quests import BoostShopView
from phantycoon.cogs.shop import ShopView
from phantycoon.cogs.top import TopView
from phantycoon.cogs.upgrades import UpgradesView


@bot.listen("on_ready")
async def register_persistent_interface():
    if getattr(bot, "_main_interface_registered", False):
        return
    bot.add_view(HelpView(None))
    bot.add_view(ShopView(None))
    bot.add_view(ProfileView(None))
    bot.add_view(ClanView(None))
    bot.add_view(TopView(None))
    bot.add_view(UpgradesView(None))
    bot.add_view(PrestigeShopView(None))
    bot.add_view(BoostShopView(None))
    inventory_view = disnake.ui.View(timeout=None)
    inventory_view.add_item(InventorySelect())
    bot.add_view(inventory_view)
    bot._main_interface_registered = True
