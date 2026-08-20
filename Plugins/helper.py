# Manga-DL — Asa Bot
from pyrogram import Client, filters, enums
from pyrogram.types import InputMediaPhoto
from config import Config
from Database.database import DB
import random
import logging

logger = logging.getLogger(__name__)


def admin_filter(_, client, update):
    try:
        uid = update.from_user.id
        return uid == Config.USER_ID or uid in getattr(DB, "ADMINS", [])
    except Exception:
        return False


admin = filters.create(admin_filter)

user_states = {}
user_data = {}

WAITING_RENAME_DB = "WAITING_RENAME_DB"
WAITING_THUMBNAIL = "WAITING_THUMBNAIL"
WAITING_WATERMARK = "WAITING_WATERMARK"
WAITING_CHANNEL_ID = "WAITING_CHANNEL_ID"
WAITING_DUMP_CHANNEL = "WAITING_DUMP_CHANNEL"
WAITING_CHAPTER_INPUT = "WAITING_CHAPTER_INPUT"


def get_styled_text(text: str) -> str:
    return f"<blockquote><i>{text}</i></blockquote>"


async def check_ban(user_id):
    return await DB.is_user_banned(user_id)


def get_random_pic():
    if hasattr(Config, "PICS") and Config.PICS:
        return random.choice(Config.PICS)
    return "https://ibb.co/8gBTKm9R"


async def edit_msg_with_pic(message, text, buttons):
    pic = get_random_pic()
    try:
        if message.photo:
            await message.edit_media(
                media=InputMediaPhoto(media=pic, caption=text),
                reply_markup=buttons,
            )
        else:
            await message.delete()
            await message.reply_photo(
                photo=pic, caption=text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML,
            )
    except Exception:
        try:
            await message.delete()
            await message.reply_photo(pic, caption=text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
        except Exception:
            try:
                await message.edit_text(text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
            except Exception as e:
                logger.error(f"edit_msg_with_pic: {e}")


async def check_fsub(client, user_id):
    try:
        fsub_channels = await DB.get_fsub_channels()
        if not fsub_channels:
            return []
        missing = []
        for ch in fsub_channels:
            cid = ch.get("id") if isinstance(ch, dict) else ch
            try:
                member = await client.get_chat_member(cid, user_id)
                if member.status in (enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED):
                    title = ch.get("title", str(cid)) if isinstance(ch, dict) else str(cid)
                    url = ch.get("url", "https://t.me/Asa_Mikata373") if isinstance(ch, dict) else "https://t.me/Asa_Mikata373"
                    missing.append({"title": title, "url": url})
            except Exception:
                continue
        return missing
    except Exception as e:
        logger.error(f"check_fsub: {e}")
        return []
