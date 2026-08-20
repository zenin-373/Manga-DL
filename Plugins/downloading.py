# Manga-DL — Asa Bot
import aiohttp
import asyncio
import logging
from pathlib import Path
from PIL import Image
import io

logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self, Config):
        self.Config = Config
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"})
        return self

    async def __aexit__(self, *a):
        if self.session:
            await self.session.close()

    async def download_images(self, urls, chapter_dir, progress=None, headers=None):
        chapter_dir = Path(chapter_dir)
        chapter_dir.mkdir(parents=True, exist_ok=True)
        total = len(urls)
        ok = 0
        for i, url in enumerate(urls):
            try:
                async with self.session.get(url, headers=headers or {}) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.read()
                    if len(data) > getattr(self.Config, "MAX_IMAGE_SIZE", 10*1024*1024):
                        continue
                    ext = ".jpg"
                    path = chapter_dir / f"{i:04d}{ext}"
                    path.write_bytes(data)
                    ok += 1
            except Exception as e:
                logger.error(f"img {i}: {e}")
            if progress:
                try:
                    await progress(i + 1, total)
                except Exception:
                    pass
        logger.info(f"Downloaded {ok}/{total} images")
        return ok > 0

    async def download_cover(self, url, path, headers=None):
        try:
            async with self.session.get(url, headers=headers or {}) as resp:
                if resp.status == 200:
                    Path(path).write_bytes(await resp.read())
                    return True
        except Exception as e:
            logger.error(f"cover: {e}")
        return False

    def create_chapter_file(self, chapter_dir, manga_title, chapter_num, chapter_title,
                            file_type="pdf", intro=None, outro=None, quality=None,
                            watermark=None, password=None):
        chapter_dir = Path(chapter_dir)
        images = sorted(chapter_dir.glob("*.jpg")) + sorted(chapter_dir.glob("*.png"))
        if not images:
            images = sorted([p for p in chapter_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}])
        if not images:
            return None
        out = chapter_dir.parent / f"chapter_{chapter_num}.pdf"
        try:
            pil_images = []
            for p in images:
                im = Image.open(p).convert("RGB")
                pil_images.append(im)
            if not pil_images:
                return None
            first, rest = pil_images[0], pil_images[1:]
            first.save(out, "PDF", save_all=True, append_images=rest)
            for im in pil_images:
                im.close()
            return out
        except Exception as e:
            logger.error(f"create_chapter_file: {e}")
            return None
