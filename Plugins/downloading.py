# Manga-DL — Asa Bot
import aiohttp
import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://mangadex.org/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


class Downloader:
    def __init__(self, Config):
        self.Config = Config
        self.session = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=120, connect=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, *a):
        if self.session:
            await self.session.close()

    async def download_images(self, urls, chapter_dir, progress=None, headers=None):
        chapter_dir = Path(chapter_dir)
        chapter_dir.mkdir(parents=True, exist_ok=True)
        total = len(urls)
        if total == 0:
            logger.error("download_images: empty url list")
            return False

        hdrs = dict(DEFAULT_HEADERS)
        if headers:
            hdrs.update(headers)

        ok = 0
        for i, url in enumerate(urls):
            try:
                async with self.session.get(url, headers=hdrs) as resp:
                    if resp.status != 200:
                        logger.error(f"img {i} HTTP {resp.status}")
                        continue
                    data = await resp.read()
                    if len(data) < 100:
                        continue
                    if len(data) > getattr(self.Config, "MAX_IMAGE_SIZE", 10 * 1024 * 1024):
                        continue
                    # detect extension
                    ext = ".jpg"
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                    if "png" in ctype:
                        ext = ".png"
                    elif "webp" in ctype:
                        ext = ".webp"
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
            hdrs = dict(DEFAULT_HEADERS)
            if headers:
                hdrs.update(headers)
            async with self.session.get(url, headers=hdrs) as resp:
                if resp.status == 200:
                    Path(path).write_bytes(await resp.read())
                    return True
        except Exception as e:
            logger.error(f"cover: {e}")
        return False

    def create_chapter_file(
        self,
        chapter_dir,
        manga_title,
        chapter_num,
        chapter_title,
        file_type="pdf",
        intro=None,
        outro=None,
        quality=None,
        watermark=None,
        password=None,
    ):
        chapter_dir = Path(chapter_dir)
        images = sorted(
            [
                p
                for p in chapter_dir.iterdir()
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            ]
        )
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
