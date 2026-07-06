import logging

import disnake

logger = logging.getLogger(__name__)


def _is_already_acknowledged(error: disnake.HTTPException) -> bool:
    return getattr(error, "code", None) == 40060


async def safe_defer(inter, *, ephemeral: bool = False, with_message: bool = True) -> bool:
    if inter.response.is_done():
        return False

    try:
        await inter.response.defer(ephemeral=ephemeral, with_message=with_message)
        return True
    except disnake.NotFound:
        logger.warning("Interaction expired before defer")
    except disnake.HTTPException as error:
        if _is_already_acknowledged(error):
            return False
        logger.exception("Failed to defer interaction")
    return False


async def safe_send(inter, *args, **kwargs):
    try:
        if inter.response.is_done():
            return await inter.followup.send(*args, **kwargs)
        await inter.response.send_message(*args, **kwargs)
        return None
    except disnake.NotFound:
        logger.warning("Interaction expired before send")
    except disnake.HTTPException as error:
        if _is_already_acknowledged(error):
            try:
                return await inter.followup.send(*args, **kwargs)
            except disnake.NotFound:
                logger.warning("Interaction expired before followup send")
            except disnake.HTTPException:
                logger.exception("Failed to send interaction followup")
            return None
        logger.exception("Failed to send interaction response")
    return None


async def safe_edit(inter, *args, **kwargs):
    try:
        if inter.response.is_done():
            return await inter.message.edit(*args, **kwargs)
        await inter.response.edit_message(*args, **kwargs)
        return None
    except disnake.NotFound:
        logger.warning("Interaction expired before edit")
    except disnake.HTTPException:
        logger.exception("Failed to edit interaction response")
    return None
