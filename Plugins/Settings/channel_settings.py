# Manga-DL — Asa Bot
from pyrogram import Client, filters, enums
from Database.database import DB
from Plugins.helper import user_states, WAITING_CHANNEL_ID, WAITING_DUMP_CHANNEL
import logging

logger = logging.getLogger(__name__)


@Client.on_callback_query(filters.regex("^set_upload_ch$"))
async def set_upload_ch_cb(client, cq):
    user_states[cq.from_user.id] = {"state": WAITING_CHANNEL_ID}
    await cq.answer()
    await cq.message.reply(
        "📤 <b>Set Upload Channel</b>\n\n"
        "Forward a message from the channel, or send the channel ID\n"
        "(e.g. <code>-100xxxxxxxxxx</code>).\n\n"
        "Bot must be admin in that channel.\n"
        "/cancel to abort.",
        parse_mode=enums.ParseMode.HTML,
    )


@Client.on_callback_query(filters.regex("^set_dump_ch$"))
async def set_dump_ch_cb(client, cq):
    user_states[cq.from_user.id] = {"state": WAITING_DUMP_CHANNEL}
    await cq.answer()
    await cq.message.reply(
        "📥 <b>Set Dump Channel</b>\n\n"
        "Forward a message from the channel, or send the channel ID\n"
        "(e.g. <code>-100xxxxxxxxxx</code>).\n\n"
        "Bot must be admin in that channel.\n"
        "/cancel to abort.",
        parse_mode=enums.ParseMode.HTML,
    )
