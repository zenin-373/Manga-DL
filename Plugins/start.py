# Manga-DL — Asa Bot
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from Plugins.helper import get_random_pic, get_styled_text, user_states

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    text = (
        "<blockquote>Powered By @Asa_Mikata373</blockquote>\n\n"
        "<b>Manga-DL — Asa Bot</b>\n\n"
        "Search and download manga chapters.\n"
        "Use /search &lt;name&gt; or /help."
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Help", callback_data="help_cb")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")],
        [InlineKeyboardButton("📢 Channel", url="https://t.me/Asa_Mikata373"),
         InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/Asa_Mikata373")],
    ])
    try:
        await message.reply_photo(get_random_pic(), caption=text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
    except Exception:
        await message.reply(text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command(["settings", "setting"]) & filters.private)
async def settings_cmd(client, message):
    try:
        from Plugins.Settings.main_settings import settings_main_menu
        await settings_main_menu(client, message, edit=False)
    except Exception as e:
        logger.error(f"settings_cmd: {e}")
        await message.reply(f"❌ Settings failed: <code>{e}</code>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    text = (
        "<blockquote>Powered By @Asa_Mikata373</blockquote>\n\n"
        "<b>How to use</b>\n"
        "• /search one piece — search manga\n"
        "• Pick source → manga → chapters / range / DOWNLOAD ALL\n"
        "• /settings — dump & upload channels\n"
        "• /cancel — stop current download queue\n\n"
        "Need help? @Asa_Mikata373"
    )
    await message.reply(text, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_cmd(client, message):
    """Cancel input wait AND any running download/queue."""
    uid = message.from_user.id
    user_states.pop(uid, None)
    bot = getattr(client, "bot_instance", None)
    if bot is not None and hasattr(bot, "request_cancel"):
        bot.request_cancel()
        await message.reply(
            "🛑 <b>Cancel requested</b>\n"
            "Stopping current download / queue after this step.\n"
            "Send /search to start again.",
            parse_mode=enums.ParseMode.HTML,
        )
    else:
        await message.reply("✅ Cleared. Nothing was running.")

@Client.on_callback_query(filters.regex("^help_cb$"))
async def help_cb(client, cq):
    await help_cmd(client, cq.message)
    await cq.answer()

@Client.on_callback_query(filters.regex("^stats_close$"))
async def close_cb(client, cq):
    try:
        await cq.message.delete()
    except Exception:
        pass
    await cq.answer()
