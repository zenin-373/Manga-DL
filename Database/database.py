# Manga-DL — Asa Bot
import motor.motor_asyncio
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)


class Master:
    def __init__(self, DB_URL, DB_NAME):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URL)
        self.db = self.dbclient[DB_NAME]
        self.ADMINS = []

    def new_user(self, id, username=None):
        return dict(id=id, username=username, join_date=datetime.utcnow(), ban_status=dict(is_banned=False))

    async def add_user(self, client, message):
        try:
            user = message.from_user
            if not await self.is_user_exist(user.id):
                await self.db.users.insert_one(self.new_user(user.id, user.username))
        except Exception as e:
            logger.error(f"add_user: {e}")

    async def is_user_exist(self, id):
        try:
            return bool(await self.db.users.find_one({"id": int(id)}))
        except Exception:
            return False

    async def is_user_banned(self, id):
        try:
            user = await self.db.users.find_one({"id": int(id)})
            return bool(user and user.get("ban_status", {}).get("is_banned"))
        except Exception:
            return False

    async def get_all_users(self):
        try:
            return await self.db.users.find({}).to_list(length=None)
        except Exception:
            return []

    async def refresh_admins(self):
        try:
            docs = await self.db.admins.find({}).to_list(length=None)
            self.ADMINS = [int(d["id"]) for d in docs if d.get("id") is not None]
            if Config.USER_ID and int(Config.USER_ID) not in self.ADMINS:
                self.ADMINS.append(int(Config.USER_ID))
        except Exception as e:
            logger.error(f"refresh_admins: {e}")
            self.ADMINS = [int(Config.USER_ID)] if Config.USER_ID else []

    async def is_admin(self, user_id):
        try:
            if int(user_id) == int(Config.USER_ID):
                return True
            return int(user_id) in self.ADMINS
        except Exception:
            return False

    async def add_admin(self, user_id):
        try:
            await self.db.admins.update_one({"id": int(user_id)}, {"$set": {"id": int(user_id)}}, upsert=True)
            await self.refresh_admins()
            return True
        except Exception as e:
            logger.error(f"add_admin: {e}")
            return False

    async def remove_admin(self, user_id):
        try:
            await self.db.admins.delete_one({"id": int(user_id)})
            await self.refresh_admins()
            return True
        except Exception as e:
            logger.error(f"remove_admin: {e}")
            return False

    async def get_admins(self):
        try:
            return await self.db.admins.find({}).to_list(length=None)
        except Exception:
            return []

    async def get_config(self, key, default=None):
        try:
            doc = await self.db.config.find_one({"_id": "main"}) or {}
            return doc.get(key, default)
        except Exception:
            return default

    async def set_config(self, key, value):
        try:
            await self.db.config.update_one({"_id": "main"}, {"$set": {key: value}}, upsert=True)
            return True
        except Exception as e:
            logger.error(f"set_config: {e}")
            return False

    async def get_default_channel(self):
        return await self.get_config("upload_channel") or await self.get_config("default_channel")

    async def set_default_channel(self, channel_id):
        return await self.set_config("upload_channel", int(channel_id) if channel_id is not None else None)

    async def get_format(self):
        return await self.get_config("filename_format", "{manga_name} [Ch-{chapter}]")

    async def set_format(self, fmt):
        return await self.set_config("filename_format", fmt)

    async def get_caption(self):
        return await self.get_config("caption")

    async def set_caption(self, caption):
        return await self.set_config("caption", caption)

    async def get_thumbnail(self):
        return await self.get_config("thumbnail")

    async def get_watermark(self):
        return await self.get_config("watermark")

    async def set_watermark(self, text, position=None, color=None, opacity=None, font_size=None):
        try:
            data = {"text": text, "position": position, "color": color, "opacity": opacity, "font_size": font_size}
            await self.set_config("watermark", data)
            return True
        except Exception as e:
            logger.error(f"set_watermark: {e}")
            return False

    async def delete_watermark(self):
        try:
            await self.set_config("watermark", None)
            return True
        except Exception:
            return False

    async def is_chapter_uploaded(self, chapter_id):
        try:
            return bool(await self.db.chapters.find_one({"chapter_id": str(chapter_id)}))
        except Exception:
            return False

    async def manga_store_data(self, chapter_id, manga_id, manga_title, chapter_num, file_id=None):
        try:
            await self.db.chapters.update_one(
                {"chapter_id": str(chapter_id)},
                {"$set": {
                    "chapter_id": str(chapter_id), "manga_id": str(manga_id),
                    "manga_title": manga_title, "chapter_num": str(chapter_num),
                    "file_id": file_id, "uploaded_at": datetime.utcnow(),
                }},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"manga_store_data: {e}")

    async def get_chapter_file(self, chapter_id):
        try:
            doc = await self.db.chapters.find_one({"chapter_id": str(chapter_id)})
            return doc.get("file_id") if doc else None
        except Exception:
            return None

    async def set_upload_state(self, manga_id, title, idx, current, total):
        try:
            await self.db.upload_state.update_one(
                {"_id": "current"},
                {"$set": {"manga_id": manga_id, "title": title, "idx": idx, "current": current, "total": total}},
                upsert=True,
            )
        except Exception:
            pass

    async def clear_upload_state(self):
        try:
            await self.db.upload_state.delete_one({"_id": "current"})
        except Exception:
            pass

    async def get_monitoring_status(self):
        return bool(await self.get_config("monitoring", False))

    async def set_monitoring_status(self, status: bool):
        return await self.set_config("monitoring", bool(status))

    async def get_check_interval(self):
        try:
            return int(await self.get_config("check_interval", 300) or 300)
        except Exception:
            return 300

    async def get_auto_update_channels(self):
        try:
            return await self.db.auto_update_channels.find({}).to_list(length=None)
        except Exception:
            return []

    async def clear_auto_update_channels(self):
        try:
            await self.db.auto_update_channels.delete_many({})
            return True
        except Exception as e:
            logger.error(f"clear_auto_update_channels: {e}")
            return False

    async def add_auto_update_channel(self, cid, title=None):
        try:
            await self.db.auto_update_channels.update_one(
                {"id": int(cid)}, {"$set": {"id": int(cid), "title": title or str(cid)}}, upsert=True,
            )
            return True
        except Exception as e:
            logger.error(f"add_auto_update_channel: {e}")
            return False

    async def get_fsub_channels(self):
        try:
            return await self.db.fsub_channels.find({}).to_list(length=None)
        except Exception:
            return []

    async def add_fsub_channel(self, cid):
        try:
            await self.db.fsub_channels.update_one({"id": int(cid)}, {"$set": {"id": int(cid)}}, upsert=True)
            return True
        except Exception:
            return False

    async def remove_fsub_channel(self, cid):
        try:
            await self.db.fsub_channels.delete_one({"id": int(cid)})
            return True
        except Exception:
            return False

    async def show_channels(self):
        try:
            return await self.db.channels.find({}).to_list(length=None)
        except Exception:
            return []

    async def get_channel_mode(self, cid):
        try:
            doc = await self.db.channels.find_one({"id": int(cid)})
            return (doc or {}).get("mode", "off")
        except Exception:
            return "off"

    async def set_channel_mode(self, cid, mode):
        try:
            await self.db.channels.update_one({"id": int(cid)}, {"$set": {"id": int(cid), "mode": mode}}, upsert=True)
            return True
        except Exception:
            return False


DB = Master(Config.DB_URL, Config.DB_NAME)
