# Manga-DL — Asa Bot
from pyrogram import Client, filters
from Plugins.helper import (
    user_states,
    WAITING_CHAPTER_INPUT,
    WAITING_CHANNEL_ID,
    WAITING_DUMP_CHANNEL,
)
from Database.database import DB
import logging

logger = logging.getLogger(__name__)


def _extract_channel_id(message):
    """From forward or plain text ID."""
    if message.forward_from_chat:
        return message.forward_from_chat.id
    text = (message.text or message.caption or "").strip()
    if not text:
        return None
    text = text.replace("https://t.me/c/", "").split("/")[0]
    try:
        return int(text)
    except Exception:
        return None


@Client.on_message(
    filters.private
    & (filters.text | filters.forwarded)
    & ~filters.command(["start", "help", "settings", "setting", "search", "status", "cancel"])
)
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
        return

    if state == WAITING_CHANNEL_ID:
        cid = _extract_channel_id(message)
        user_states.pop(uid, None)
        if cid is None:
            await message.reply("Invalid channel. Send ID or forward from channel.")
            return
        try:
            await DB.set_default_channel(cid)
            await message.reply(
                f"✅ Upload channel set to <code>{cid}</code>",
                parse_mode="html",
            )
        except Exception as e:
            await message.reply(f"❌ Failed: {e}")
        return

    if state == WAITING_DUMP_CHANNEL:
        cid = _extract_channel_id(message)
        user_states.pop(uid, None)
        if cid is None:
            await message.reply("Invalid channel. Send ID or forward from channel.")
            return
        try:
            await DB.set_config("dump_channel", int(cid))
            await message.reply(
                f"✅ Dump channel set to <code>{cid}</code>",
                parse_mode="html",
            )
        except Exception as e:
            await message.reply(f"❌ Failed: {e}")
        return
