# Manga-DL — Asa Bot
from pathlib import Path
import shutil
import logging
logger = logging.getLogger(__name__)

class DriveMountHandler:
    def __init__(self, mount_path=""):
        self.mount_path = Path(mount_path) if mount_path else None

    def is_available(self):
        return bool(self.mount_path and self.mount_path.exists())

    def save_chapter(self, file_path, manga_title, chapter_num, chapter_title="", manga_info=None):
        if not self.is_available():
            return None
        try:
            safe = "".join(c for c in manga_title if c.isalnum() or c in " -_")[:80].strip()
            dest_dir = self.mount_path / safe
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / Path(file_path).name
            shutil.copy2(file_path, dest)
            return str(dest)
        except Exception as e:
            logger.error(f"Drive save: {e}")
            return None
