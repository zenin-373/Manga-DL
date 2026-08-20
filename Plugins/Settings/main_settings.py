# Manga-DL — Asa Bot
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from Database.database import DB
from Plugins.helper import admin, get_styled_text, edit_msg_with_pic
from config import Config

async def settings_main_menu(client, message_or_cq, edit=False):
    text = get_styled_text(
        "<b>⚙️ Settings</b>\n\nConfigure dump/upload channels, monitoring, and more."
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channels", callback_data="channel_settings")],
        [InlineKeyboardButton("📡 Monitor", callback_data="monitor_settings")],
        [InlineKeyboardButton("📁 Files", callback_data="file_settings")],
        [InlineKeyboardButton("⬅ Close", callback_data="stats_close")],
    ])
    msg = message_or_cq.message if hasattr(message_or_cq, "message") else message_or_cq
    if edit and hasattr(message_or_cq, "message"):
        await edit_msg_with_pic(message_or_cq.message, text, buttons)
    else:
        await msg.reply_photo(
            photo=Config.PICS[0] if Config.PICS else "https://ibb.co/8gBTKm9R",
            caption=text,
            reply_markup=buttons,
            parse_mode=enums.ParseMode.HTML,
        )

@Client.on_callback_query(filters.regex("^settings_menu$"))
async def settings_menu_cb(client, cq):
    await settings_main_menu(client, cq, edit=True)
    await cq.answer()
