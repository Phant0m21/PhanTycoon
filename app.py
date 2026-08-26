from phantycoon.bot import bot
from phantycoon.config import TOKEN
from phantycoon.database import init_db


def load_extensions() -> None:
    import phantycoon.cogs.dev
    import phantycoon.cogs.general
    import phantycoon.cogs.top
    import phantycoon.cogs.help
    import phantycoon.cogs.maintenance
    import phantycoon.cogs.captcha
    import phantycoon.cogs.moderation
    import phantycoon.cogs.tickets
    import phantycoon.cogs.business
    import phantycoon.cogs.shop
    import phantycoon.cogs.quests
    import phantycoon.cogs.inventory
    import phantycoon.cogs.profile
    import phantycoon.cogs.games
    import phantycoon.cogs.mine
    import phantycoon.cogs.upgrades
    import phantycoon.cogs.prestige
    import phantycoon.cogs.clan
    import phantycoon.cogs.interface
    import phantycoon.events


def main() -> None:
    init_db()
    load_extensions()
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
