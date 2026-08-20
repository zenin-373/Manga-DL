# Manga-DL — Asa Bot
import logging
import asyncio
from pathlib import Path
from pyrogram import Client, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


class PyrogramHandler:
    def __init__(self, api_id, api_hash, bot_token, channel_id, user_id, plugins=None, bot_instance=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.user_id = user_id
        self.bot_instance = bot_instance
        self.app = Client(
            "manga_bot_session",
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            plugins=plugins or {"root": "Plugins"},
            in_memory=False,
        )
        if bot_instance is not None:
            self.app.bot_instance = bot_instance

    async def initialize(self):
        logger.info(f"Initializing Pyrogram with plugins: {self.app.plugins}")
        await self.app.start()
        me = await self.app.get_me()
        logger.info(f"Bot online as @{me.username}")

    async def stop(self):
        try:
            await self.app.stop()
        except Exception:
            pass

    async def send_notification(self, text):
        try:
            await self.app.send_message(self.user_id, text, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            logger.error(f"notify: {e}")

    async def upload_chapter(self, file_path, caption, thumb_path=None, progress=None):
        path = Path(file_path)
        if not path.exists():
            return None
        chat_id = self.channel_id
        if not chat_id:
            logger.error("No channel_id for upload")
            return None
        for attempt in range(3):
            try:
                logger.info(f"Uploading to {chat_id} → {path.name} ({path.stat().st_size/1024/1024:.1f}MB)")
                kwargs = dict(
                    chat_id=chat_id,
                    document=str(path),
                    caption=caption,
                    parse_mode=enums.ParseMode.HTML,
                    force_document=True,
                )
                if thumb_path and Path(thumb_path).exists():
                    kwargs["thumb"] = str(thumb_path)
                if progress:
                    kwargs["progress"] = progress
                msg = await self.app.send_document(**kwargs)
                return msg.document.file_id if msg and msg.document else True
            except Exception as e:
                logger.error(f"Upload failed (attempt {attempt+1}): {e}")
                await asyncio.sleep(2 ** attempt)
        return None

    async def send_post(self, chat_id, caption, photo_path=None, button_url=None, channel_link=None):
        buttons = []
        row = []
        if button_url:
            row.append(InlineKeyboardButton("📖 Read Manga", url=button_url))
        if channel_link:
            row.append(InlineKeyboardButton("📢 Channel", url=channel_link))
        row.append(InlineKeyboardButton("👨‍💻 Dev", url="https://t.me/Asa_Mikata373"))
        if row:
            buttons.append(row)
        markup = InlineKeyboardMarkup(buttons) if buttons else None
        try:
            if photo_path and Path(photo_path).exists():
                await self.app.send_photo(chat_id, photo_path, caption=caption, parse_mode=enums.ParseMode.HTML, reply_markup=markup)
            else:
                await self.app.send_message(chat_id, caption, parse_mode=enums.ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"send_post: {e}")
