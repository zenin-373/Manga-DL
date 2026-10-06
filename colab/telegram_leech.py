"""Telegram leech helpers for WeebCentral Colab."""
from __future__ import annotations
import html, logging
from pathlib import Path
logger = logging.getLogger(__name__)

def build_rich_caption(manga_info, total_chapters=0):
    title = manga_info.get("title") or "Unknown"
    authors = manga_info.get("authors") or []
    tags = manga_info.get("tags") or []
    status = manga_info.get("status") or "Unknown"
    released = manga_info.get("released") or ""
    manga_type = manga_info.get("type") or ""
    series_url = manga_info.get("series_url") or ""
    lines = [f"<blockquote><b>📖 {html.escape(str(title))}</b></blockquote>", ""]
    meta = []
    if released: meta.append(f"📅 Year: <code>{html.escape(str(released))}</code>")
    if status: meta.append(f"📊 Status: <b>{html.escape(str(status))}</b>")
    if manga_type: meta.append(f"📚 Type: <code>{html.escape(str(manga_type))}</code>")
    if total_chapters: meta.append(f"📑 Total Chapters: <code>{total_chapters}</code>")
    if authors: meta.append(f"✍️ Author: {html.escape(', '.join(authors[:4]))}")
    if tags: meta.append(f"🏷️ Tags: {html.escape(', '.join(tags[:8]))}")
    meta.append("🌐 Source: WeebCentral")
    meta.append("🗣 Language: English")
    if series_url: meta.append(f'<a href="{html.escape(series_url)}">WeebCentral link</a>')
    lines.append("<blockquote>" + "\n".join(meta) + "</blockquote>")
    return "\n".join(lines)

def build_pdf_caption(manga_title, chapter_num, chapter_title=""):
    lines = [str(manga_title), f"Chapter {chapter_num}"]
    if chapter_title and str(chapter_title).strip():
        lines.append(f"<blockquote>{html.escape(str(chapter_title).strip())}</blockquote>")
    return "\n".join(lines)

def build_dump_info(manga_title, chapter_num, chapter_title=""):
    text = f"<b>{html.escape(str(manga_title))}</b>\nChapter <code>{html.escape(str(chapter_num))}</code>"
    if chapter_title and str(chapter_title).strip():
        text += f"\n<blockquote>{html.escape(str(chapter_title).strip())}</blockquote>"
    return text

def download_cover(cover_url, dest):
    if not cover_url: return None
    try:
        import requests
        dest = Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(cover_url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://weebcentral.com/"}, timeout=30)
        r.raise_for_status(); dest.write_bytes(r.content); return str(dest)
    except Exception as e:
        logger.warning(f"cover: {e}"); return None

class TelegramLeech:
    def __init__(self, api_id, api_hash, bot_token, user_id, dump_channel, upload_channel=None, channel_link="https://t.me/Asa_Mikata373", session_name="weeb_leech_session"):
        self.api_id, self.api_hash, self.bot_token = int(api_id), api_hash, bot_token
        self.user_id = int(user_id)
        self.dump_channel = int(dump_channel) if dump_channel else None
        self.upload_channel = int(upload_channel) if upload_channel else None
        self.channel_link = channel_link
        self.session_name = session_name
        self.app = None
        self._posted_info = set()

    async def start(self):
        from pyrogram import Client
        self.app = Client(self.session_name, api_id=self.api_id, api_hash=self.api_hash, bot_token=self.bot_token, in_memory=False)
        await self.app.start()
        me = await self.app.get_me()
        print(f"Online as @{me.username}")
        return me

    async def stop(self):
        if self.app:
            try: await self.app.stop()
            except Exception: pass

    async def notify(self, text):
        if not self.app or not self.user_id: return
        try: await self.app.send_message(self.user_id, text)
        except Exception as e: print("notify:", e)

    async def post_series_poster(self, manga_info, total_chapters, cover_path=None):
        key = manga_info.get("series_url") or manga_info.get("title")
        if key in self._posted_info: return
        target = self.upload_channel or self.dump_channel
        if not target or not self.app: return
        from pyrogram import enums
        caption = build_rich_caption(manga_info, total_chapters)
        try:
            if cover_path and Path(cover_path).exists():
                await self.app.send_photo(target, cover_path, caption=caption, parse_mode=enums.ParseMode.HTML)
            else:
                await self.app.send_message(target, caption, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
            self._posted_info.add(key)
            print("Series poster sent")
        except Exception as e:
            print("poster failed:", e)

    async def upload_chapter_pdf(self, pdf_path, manga_title, chapter_num, chapter_title="", series_url="", thumb_path=None):
        if not self.app or not self.dump_channel: return False
        if not pdf_path or not Path(pdf_path).exists(): return False
        from pyrogram import enums
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        caption = build_pdf_caption(manga_title, chapter_num, chapter_title)
        path = Path(pdf_path)
        async def _send_doc(chat_id, with_buttons=False):
            kw = dict(chat_id=chat_id, document=str(path), caption=caption, parse_mode=enums.ParseMode.HTML, force_document=True)
            if thumb_path and Path(thumb_path).exists(): kw["thumb"] = thumb_path
            await self.app.send_document(**kw)
            if with_buttons:
                row = []
                if series_url: row.append(InlineKeyboardButton("Read", url=series_url))
                if self.channel_link:
                    row.append(InlineKeyboardButton("Channel", url=self.channel_link))
                    row.append(InlineKeyboardButton("Dev", url=self.channel_link))
                info = build_dump_info(manga_title, chapter_num, chapter_title)
                await self.app.send_message(chat_id, info, parse_mode=enums.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([row]) if row else None, disable_web_page_preview=True)
        try:
            await _send_doc(self.dump_channel, with_buttons=True)
            if self.upload_channel and int(self.upload_channel) != int(self.dump_channel):
                await _send_doc(self.upload_channel, with_buttons=False)
            await self.notify(f"Posted: {manga_title} - Ch {chapter_num}")
            return True
        except Exception as e:
            print("upload failed:", e)
            await self.notify(f"Upload failed Ch {chapter_num}: {e}")
            return False
