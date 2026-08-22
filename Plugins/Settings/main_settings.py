# Manga-DL — Asa Bot
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from Database.database import DB
from Plugins.helper import get_styled_text, edit_msg_with_pic, get_random_pic
from config import Config
import logging

logger = logging.getLogger(__name__)


async def settings_main_menu(client, message_or_cq, edit=False):
    """Open main settings. Safe fallbacks if photo fails."""
    try:
        dump = await DB.get_config("dump_channel")
        upload = await DB.get_default_channel()
        mon = await DB.get_monitoring_status()
    except Exception:
        dump = upload = None
        mon = False

    text = (
        "<blockquote>Powered By @Asa_Mikata373</blockquote>\n\n"
        "<b>⚙️ Settings</b>\n\n"
        f"📤 Upload channel: <code>{upload or 'not set'}</code>\n"
        f"📥 Dump channel: <code>{dump or 'not set'}</code>\n"
        f"📡 Monitor: <b>{'ON' if mon else 'OFF'}</b>\n"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Set Upload Channel", callback_data="set_upload_ch")],
        [InlineKeyboardButton("📥 Set Dump Channel", callback_data="set_dump_ch")],
        [
            InlineKeyboardButton("📡 Monitor ON", callback_data="monitor_on"),
            InlineKeyboardButton("Monitor OFF", callback_data="monitor_off"),
        ],
        [InlineKeyboardButton("🔄 Refresh", callback_data="settings_menu")],
        [InlineKeyboardButton("⬅ Close", callback_data="stats_close")],
    ])

    try:
        if edit and hasattr(message_or_cq, "message"):
            msg = message_or_cq.message
            try:
                await edit_msg_with_pic(msg, text, buttons)
            except Exception:
                try:
                    await msg.edit_text(text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
                except Exception:
                    await msg.reply(text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
            return

        # /settings command — message is a Message
        msg = message_or_cq
        try:
            await msg.reply_photo(
                photo=get_random_pic(),
                caption=text,
                reply_markup=buttons,
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception as e:
            logger.warning(f"settings photo failed: {e}")
            await msg.reply(text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        logger.error(f"settings_main_menu: {e}")
        try:
            target = message_or_cq.message if hasattr(message_or_cq, "message") else message_or_cq
            await target.reply(f"❌ Settings error: <code>{e}</code>", parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^settings_menu$"))
async def settings_menu_cb(client, cq):
    await settings_main_menu(client, cq, edit=True)
    await cq.answer()
