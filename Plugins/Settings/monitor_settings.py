# Manga-DL — Asa Bot
from pyrogram import Client, filters
from Database.database import DB
from Plugins.Settings.main_settings import settings_main_menu
import logging

logger = logging.getLogger(__name__)


@Client.on_callback_query(filters.regex("^monitor_on$"))
async def monitor_on_cb(client, cq):
    try:
        await DB.set_monitoring_status(True)
        await cq.answer("Monitor ON", show_alert=True)
    except Exception as e:
        await cq.answer(str(e)[:100], show_alert=True)
    await settings_main_menu(client, cq, edit=True)


@Client.on_callback_query(filters.regex("^monitor_off$"))
async def monitor_off_cb(client, cq):
    try:
        await DB.set_monitoring_status(False)
        await cq.answer("Monitor OFF", show_alert=True)
    except Exception as e:
        await cq.answer(str(e)[:100], show_alert=True)
    await settings_main_menu(client, cq, edit=True)
