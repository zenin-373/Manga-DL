# Manga-DL — Asa Bot
import sys
import os
import json
import asyncio
import shutil
import logging
import gc
from pathlib import Path

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from pyrogram import enums, idle
import aiofiles
from aiohttp import web
from Plugins.web_server import web_server
from config import Config
from Plugins.downloading import Downloader
from Plugins.Sites.mangadex import MangaDexAPI
from Plugins.Sites.webcentral import WebCentralAPI
from Plugins.Sites.mangaforest import MangaForestAPI
from Plugins.Sites.mangakakalot import MangakakalotAPI
from Plugins.Sites.allmanga import AllMangaAPI
from Plugins.uploading import PyrogramHandler
from Plugins.gdrive import DriveMountHandler
from Database.database import *
from Plugins.status_ui import TaskStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

class MangaDexBot:
    def __init__(self, Config):
        self.Config = Config
        self.download_dir = Path(Config.DOWNLOAD_DIR)
        self.state_file = Path(Config.STATE_FILE)
        self.cache_file = Path(Config.CACHE_FILE)
        self.download_dir.mkdir(exist_ok=True)
        self.state = {"uploaded_chapters": []}
        self.manga_cache = {}
        self.db_master = DB
        os.chdir(Path(__file__).parent)
        self.plugins = {"root": "Plugins"}
        self.upload_channel_id = None
        self.dump_channel_id = None
        self.filename_format = Config.DEFAULT_FILENAME_FORMAT
        self.has_custom_thumbnail = False
        self.telegram = PyrogramHandler(Config.API_ID, Config.API_HASH, Config.BOT_TOKEN, self.upload_channel_id, Config.USER_ID, plugins=self.plugins, bot_instance=self)
        self.processing = False
        self.drive = None
        self.upload_mode = getattr(Config, "UPLOAD_MODE", "both")
        self.posted_manga_info = set()

    async def resolve_dynamic_config(self):
        if not self.Config.USE_DATABASE:
            return
        try:
            db_channel = await self.db_master.get_default_channel()
            if db_channel not in (None, "", "None"):
                self.upload_channel_id = int(db_channel)
            else:
                self.upload_channel_id = None
            if self.telegram:
                self.telegram.channel_id = self.upload_channel_id
        except Exception as e:
            logger.error(f"Channel load error: {e}")
        try:
            dump_channel = await self.db_master.get_config("dump_channel")
            if dump_channel not in (None, "", "None"):
                self.dump_channel_id = int(dump_channel)
            else:
                self.dump_channel_id = self.upload_channel_id
        except Exception as e:
            logger.error(f"Dump Channel load error: {e}")
        try:
            db_format = await self.db_master.get_format()
            if db_format and str(db_format).strip():
                self.filename_format = db_format
        except Exception:
            self.filename_format = self.Config.DEFAULT_FILENAME_FORMAT
        try:
            self.has_custom_thumbnail = bool(await self.db_master.get_thumbnail())
        except Exception:
            self.has_custom_thumbnail = False
        try:
            drive_path = await self.db_master.get_config("drive_mount_path") or getattr(self.Config, "DRIVE_MOUNT_PATH", "") or ""
            self.drive = DriveMountHandler(drive_path) if drive_path else None
            if self.drive and not self.drive.is_available():
                self.drive = None
        except Exception:
            self.drive = None
        try:
            mode = await self.db_master.get_config("upload_mode")
            self.upload_mode = mode if mode in ("telegram", "drive", "both") else getattr(self.Config, "UPLOAD_MODE", "both")
        except Exception:
            self.upload_mode = "both"

    async def load_state(self):
        if self.state_file.exists():
            try:
                async with aiofiles.open(self.state_file, 'r') as f:
                    state = json.loads(await f.read())
                    return state if "uploaded_chapters" in state else {"uploaded_chapters": []}
            except Exception:
                pass
        return {"uploaded_chapters": []}

    async def save_state(self):
        try:
            async with aiofiles.open(self.state_file, 'w') as f:
                await f.write(json.dumps(self.state, indent=2))
        except Exception as e:
            logger.error(f"State save failed: {e}")

    async def load_cache(self):
        if self.cache_file.exists():
            try:
                async with aiofiles.open(self.cache_file, 'r') as f:
                    return json.loads(await f.read())
            except Exception:
                pass
        return {}

    async def save_cache(self):
        try:
            async with aiofiles.open(self.cache_file, 'w') as f:
                await f.write(json.dumps(self.manga_cache, indent=2))
        except Exception:
            pass

    async def is_chapter_uploaded(self, chapter_id):
        if self.Config.USE_DATABASE:
            try:
                return await self.db_master.is_chapter_uploaded(chapter_id)
            except Exception:
                pass
        return chapter_id in self.state["uploaded_chapters"]

    async def mark_chapter_uploaded(self, chapter_id, manga_id, manga_title, chapter_num, file_id=None):
        if self.Config.USE_DATABASE:
            try:
                await self.db_master.manga_store_data(chapter_id, manga_id, manga_title, chapter_num, file_id)
            except Exception:
                pass
        if chapter_id not in self.state["uploaded_chapters"]:
            self.state["uploaded_chapters"].append(chapter_id)

    def cleanup_old_records(self):
        if len(self.state["uploaded_chapters"]) > 500:
            self.state["uploaded_chapters"] = self.state["uploaded_chapters"][-500:]

    async def cleanup_downloads(self):
        try:
            if self.download_dir.exists():
                await asyncio.to_thread(shutil.rmtree, self.download_dir, ignore_errors=True)
                self.download_dir.mkdir(exist_ok=True)
                gc.collect()
        except Exception:
            pass

    def _safe_cleanup(self, chapter_dir, file_path, thumb_path):
        try:
            if chapter_dir and chapter_dir.exists():
                shutil.rmtree(chapter_dir, ignore_errors=True)
            if file_path and Path(file_path).exists():
                Path(file_path).unlink(missing_ok=True)
            if thumb_path and Path(thumb_path).exists():
                Path(thumb_path).unlink(missing_ok=True)
        except Exception:
            pass

    def get_api_instance(self, source):
        s = str(source).lower()
        if s == "webcentral": return WebCentralAPI(self.Config)
        if s == "mangaforest": return MangaForestAPI(self.Config)
        if s == "mangakakalot": return MangakakalotAPI(self.Config)
        if s == "allmanga": return AllMangaAPI(self.Config)
        return MangaDexAPI(self.Config)

    def _build_rich_caption(self, manga_title, chapter_num, chapter_title="", group="Unknown", manga_info=None, drive_path=None):
        import html
        info = manga_info or {}
        lines = ["<blockquote>Powered By @Asa_Mikata373</blockquote>", "", f"<blockquote><b>📖 {html.escape(str(manga_title))}</b></blockquote>", "", f"<b>Chapter {html.escape(str(chapter_num))}</b>"]
        if chapter_title:
            lines.append(f"<blockquote>{html.escape(chapter_title)}</blockquote>")
        meta = []
        if info.get("year"): meta.append(f"📅 Year: <code>{info['year']}</code>")
        if info.get("status"): meta.append(f"📊 Status: <b>{html.escape(str(info['status']))}</b>")
        if info.get("last_volume"): meta.append(f"📚 Total Volumes: <code>{html.escape(str(info['last_volume']))}</code>")
        if info.get("last_chapter"): meta.append(f"📑 Total Chapters: <code>{html.escape(str(info['last_chapter']))}</code>")
        authors = info.get("authors") or []
        if authors: meta.append(f"✍️ Author: {html.escape(', '.join(authors[:3]))}")
        tags = info.get("tags") or []
        if tags: meta.append(f"🏷️ Tags: {html.escape(', '.join(tags[:6]))}")
        meta.append(f"🌐 Group: {html.escape(str(group))}")
        meta.append("🗣 Language: English")
        if meta:
            lines += ["", "<blockquote>" + "\n".join(meta) + "</blockquote>"]
        if drive_path:
            lines += ["", "📁 <i>Also saved to Drive</i>"]
        return "\n".join(lines)

    async def process_chapter(self, chapter):
        chapter_dir = file_path = thumb_path = None
        task_ui = None
        try:
            manga_id = chapter['manga_id']
            manga_title = chapter['manga_title']
            chapter_id = chapter['id']
            chapter_url = chapter.get('url', chapter['id'])
            chapter_num = chapter.get('number') or chapter.get('chapter') or '0'
            chapter_title = chapter.get('title') or ''
            logger.info(f"Processing: {manga_title} - Ch {chapter_num}")
            try:
                if self.telegram and self.telegram.app and Config.USER_ID:
                    task_ui = TaskStatus(self.telegram.app, int(Config.USER_ID))
                    await task_ui.start(f"{manga_title} [Ch-{chapter_num}]", "Download")
            except Exception:
                task_ui = None

            async def progress_hook(current, total, action="Processing"):
                try:
                    await self.db_master.set_upload_state(manga_id, f"[{action}] {manga_title} - Ch {chapter_num}", 1 if action=="Upload" else 0, current, total)
                except Exception:
                    pass
                if task_ui:
                    try:
                        await task_ui.update(status=action, current=current, total=total, force=(current==total))
                    except Exception:
                        pass

            if await self.is_chapter_uploaded(chapter_id):
                if task_ui: await task_ui.finish(True, detail="Already uploaded")
                return False

            raw_src = chapter.get('source') or await self.db_master.get_config('manga_source', 'mangadex') or 'mangadex'
            import re as _re
            _cid = str(chapter.get('id') or '')
            if _re.fullmatch(r'[0-9a-fA-F-]{36}', _cid):
                raw_src = 'mangadex'
            source = str(raw_src).lower()
            logger.info(f"Using source: {source}")

            if manga_id not in self.manga_cache:
                api_instance = self.get_api_instance(source)
                try:
                    if hasattr(api_instance, '__aenter__'):
                        async with api_instance as api:
                            info = await api.get_manga_info(manga_id)
                    else:
                        info = await api_instance.get_manga_info(manga_id)
                    if info:
                        self.manga_cache[manga_id] = info
                        await self.save_cache()
                except Exception as e:
                    logger.warning(f"manga info: {e}")

            manga_info = self.manga_cache.get(manga_id, {'cover_url': None})
            api_instance = self.get_api_instance(source)
            if hasattr(api_instance, '__aenter__'):
                async with api_instance as api:
                    images = await api.get_chapter_images(chapter_url)
            else:
                images = await api_instance.get_chapter_images(chapter_url)
            if not images or len(images) > 200:
                if task_ui: await task_ui.finish(False, detail="Invalid images")
                return False

            safe_manga_id = str(manga_id).replace('/', '_')[-20:]
            chapter_dir = self.download_dir / safe_manga_id / f"ch_{chapter_num}"
            source_headers = getattr(api_instance, 'headers', None)

            async with Downloader(self.Config) as downloader:
                async def dl_progress(c, t):
                    await progress_hook(c, t, "Download")
                if not await downloader.download_images(images, chapter_dir, dl_progress, headers=source_headers):
                    if task_ui: await task_ui.finish(False, detail="Download failed")
                    return False
                cover_url = manga_info.get('cover_url')
                cover_path = chapter_dir.parent / "cover.jpg" if cover_url else None
                if cover_url:
                    await downloader.download_cover(cover_url, cover_path, headers=source_headers)
                if task_ui:
                    await task_ui.update(status="Build PDF", current=0, total=1, force=True)
                file_type = await self.db_master.get_config("file_type", "pdf")
                quality = await self.db_master.get_config("image_quality")
                pdf_password = await self.db_master.get_config("pdf_password")
                watermark = await self.db_master.get_watermark()
                base_file = await asyncio.to_thread(
                    downloader.create_chapter_file, chapter_dir, manga_title, chapter_num, chapter_title,
                    file_type, None, None, quality, watermark, password=pdf_password)
                if not base_file:
                    if task_ui: await task_ui.finish(False, detail="PDF failed")
                    return False
                safe_manga = "".join(c for c in manga_title if c.isalnum() or c in " -_[]")
                safe_chap = str(chapter_num).replace('.', '-')
                try:
                    final_name = self.filename_format.format(manga_name=safe_manga, chapter=safe_chap, chapter_title=chapter_title.strip())
                except KeyError:
                    final_name = f"{safe_manga} [Ch-{safe_chap}]"
                final_name = "".join(c for c in final_name if c.isalnum() or c in " -_[]()")[:150].strip()
                ext = ".cbz" if str(file_type).lower() == "cbz" else ".pdf"
                if not final_name.lower().endswith(ext):
                    final_name += ext
                file_path = chapter_dir.parent / final_name
                if base_file != file_path:
                    base_file.rename(file_path)
                thumb_path = cover_path if cover_path and cover_path.exists() else None

                try:
                    up = await self.db_master.get_default_channel()
                    if up not in (None, "", "None"):
                        self.upload_channel_id = int(up)
                    dump = await self.db_master.get_config("dump_channel")
                    if dump not in (None, "", "None"):
                        self.dump_channel_id = int(dump)
                    if not self.dump_channel_id and self.upload_channel_id:
                        self.dump_channel_id = self.upload_channel_id
                except Exception as e:
                    logger.error(f"Channel refresh: {e}")

                target_dump = self.dump_channel_id or self.upload_channel_id
                if not target_dump:
                    if task_ui: await task_ui.finish(False, detail="No channel")
                    return False

                original_cid = self.telegram.channel_id
                async def ul_progress(c, t):
                    await progress_hook(c, t, "Upload")
                if chapter_title and str(chapter_title).strip():
                    storage_caption = f"{manga_title}\nChapter {chapter_num}\n<blockquote>{str(chapter_title).strip()}</blockquote>"
                else:
                    storage_caption = f"{manga_title}\nChapter {chapter_num}"

                self.telegram.channel_id = target_dump
                file_id = await self.telegram.upload_chapter(file_path, storage_caption, thumb_path, ul_progress)
                if not file_id:
                    self.telegram.channel_id = original_cid
                    if task_ui: await task_ui.finish(False, detail="Upload failed")
                    return False

                if self.upload_channel_id:
                    if manga_id not in self.posted_manga_info:
                        rich = self._build_rich_caption(manga_title, chapter_num, chapter_title, chapter.get("group", "Unknown"), manga_info, None)
                        self.posted_manga_info.add(manga_id)
                        try:
                            if thumb_path and Path(thumb_path).exists():
                                await self.telegram.app.send_photo(chat_id=self.upload_channel_id, photo=str(thumb_path), caption=rich, parse_mode=enums.ParseMode.HTML)
                            else:
                                await self.telegram.app.send_message(chat_id=self.upload_channel_id, text=rich, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
                        except Exception as e:
                            logger.warning(f"info post: {e}")
                    if int(self.upload_channel_id) != int(target_dump):
                        self.telegram.channel_id = self.upload_channel_id
                        try:
                            await self.telegram.upload_chapter(file_path, storage_caption, thumb_path, None)
                        except Exception as e:
                            logger.warning(f"upload ch: {e}")

                self.telegram.channel_id = original_cid
                try:
                    bot_username = self.telegram.app.me.username if self.telegram.app.me else "Bot"
                except Exception:
                    bot_username = "Bot"
                deep_link = f"https://t.me/{bot_username}?start=dl_{chapter_id}"
                import html as _html
                dump_info = f"<blockquote>Powered By @Asa_Mikata373</blockquote>\n\n<b>{_html.escape(str(manga_title))}</b>\nChapter <code>{_html.escape(str(chapter_num))}</code>"
                if chapter_title and str(chapter_title).strip():
                    dump_info += f"\n<blockquote>{_html.escape(str(chapter_title).strip())}</blockquote>"
                await self.telegram.send_post(chat_id=target_dump, caption=dump_info, photo_path=None, button_url=deep_link, channel_link="https://t.me/Asa_Mikata373")
                await self.mark_chapter_uploaded(chapter_id, manga_id, manga_title, chapter_num, file_id)
                await self.save_state()
                if task_ui:
                    await task_ui.finish(True, detail=f"Chapter {chapter_num} posted")
                return True
        except Exception as e:
            logger.error(f"Processing error: {e}")
            try:
                if task_ui: await task_ui.finish(False, detail=str(e))
            except Exception:
                pass
            return False
        finally:
            await self.db_master.clear_upload_state()
            try:
                await asyncio.to_thread(self._safe_cleanup, chapter_dir, file_path, thumb_path)
            except Exception:
                pass
        gc.collect()

    async def check_updates(self):
        if self.processing: return
        self.processing = True
        try:
            await self.resolve_dynamic_config()
            source = await self.db_master.get_config('manga_source', 'mangadex')
            api_instance = self.get_api_instance(source)
            if hasattr(api_instance, '__aenter__'):
                async with api_instance as api:
                    chapters = await api.get_latest_chapters()
            else:
                chapters = await api_instance.get_latest_chapters()
            if not chapters: return
            new_chapters = [ch for ch in chapters if not await self.is_chapter_uploaded(ch['id'])]
            for chapter in new_chapters[:self.Config.MAX_CHAPTERS_PER_CHECK]:
                if not await self.db_master.get_monitoring_status(): break
                await self.process_chapter(chapter)
                await asyncio.sleep(5)
                await self.cleanup_downloads()
            await self.save_state()
        finally:
            self.processing = False

    async def monitor_loop(self):
        while True:
            try:
                if await self.db_master.get_monitoring_status():
                    await self.check_updates()
                await asyncio.sleep(await self.db_master.get_check_interval() or 300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"monitor: {e}")
                await asyncio.sleep(60)

    async def run(self):
        logger.info("Manga-DL / Asa Bot STARTED")
        self.state = await self.load_state()
        self.manga_cache = await self.load_cache()
        await self.telegram.initialize()
        try:
            await self.db_master.refresh_admins()
        except Exception as e:
            logger.error(f"admins: {e}")
        await self.resolve_dynamic_config()
        try:
            app = web.AppRunner(await web_server())
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", self.Config.PORT).start()
        except Exception as e:
            logger.error(f"web: {e}")
        await self.db_master.set_monitoring_status(False)
        monitor_task = asyncio.create_task(self.monitor_loop())
        try:
            await idle()
        except KeyboardInterrupt:
            pass
        finally:
            monitor_task.cancel()
            await self.telegram.stop()
            await self.save_state()
            await self.save_cache()
            await self.cleanup_downloads()

async def main():
    bot = MangaDexBot(Config)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
