# Manga-DL — Asa Bot
from pyrogram import Client, filters
from Plugins.helper import user_states, WAITING_CHAPTER_INPUT
import logging
logger = logging.getLogger(__name__)

@Client.on_message(filters.private & filters.text & ~filters.command(["start","help","settings","setting","search","status"]))
async def settings_input_listener(client, message):
    uid = message.from_user.id
    state_info = user_states.get(uid)
    if not state_info:
        return
    if isinstance(state_info, str):
        state = state_info
        data = {}
    else:
        state = state_info.get("state")
        data = state_info
    if state == WAITING_CHAPTER_INPUT:
        try:
            from Plugins.search import custom_dl_input_handler
            await custom_dl_input_handler(client, message, uid, data)
        except Exception as e:
            logger.error(f"chapter input: {e}")
