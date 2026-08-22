# Manga-DL — Asa Bot
import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MangaDexAPI:
    def __init__(self, Config):
        self.Config = Config
        self.rate_limit_delay = 0.6
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MangaDL/1.0)",
            "Referer": "https://mangadex.org/",
        }

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=90, connect=30)
        self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exp_tb):
        if self.session:
            await self.session.close()
            await asyncio.sleep(0.25)

    async def api_request(self, endpoint: str, params: dict = None, retries: int = 5) -> Optional[dict]:
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        for attempt in range(retries):
            try:
                await asyncio.sleep(self.rate_limit_delay)
                url = f"{self.Config.API_BASE}{endpoint}"
                async with self.session.get(url, params=params) as response:
                    if response.status == 429:
                        wait = int(response.headers.get("Retry-After", 5))
                        logger.warning(f"Rate limited, waiting {wait}s")
                        await asyncio.sleep(wait)
                        continue
                    if response.status >= 400:
                        body = await response.text()
                        logger.error(f"API {response.status} {endpoint}: {body[:200]}")
                        if attempt < retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        return None
                    return await response.json()
            except Exception as e:
                logger.error(f"API request failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
        return None

    async def get_manga_info(self, manga_id: str) -> Optional[Dict]:
        try:
            params = {"includes[]": ["cover_art", "author", "artist"]}
            data = await self.api_request(f"/manga/{manga_id}", params)
            if not data or data.get("result") != "ok":
                return None
            manga = data["data"]
            attrs = manga["attributes"]
            title_obj = attrs.get("title", {})
            title = title_obj.get("en") or next(iter(title_obj.values()), "Unknown")
            cover_url = None
            for rel in manga.get("relationships", []):
                if rel["type"] == "cover_art":
                    cover_file = rel.get("attributes", {}).get("fileName")
                    if cover_file:
                        cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover_file}.256.jpg"
                    break
            authors, artists, tags = [], [], []
            for rel in manga.get("relationships", []):
                name = rel.get("attributes", {}).get("name")
                if not name:
                    continue
                if rel["type"] == "author":
                    authors.append(name)
                elif rel["type"] == "artist":
                    artists.append(name)
            for tag in attrs.get("tags", []):
                tag_name = tag.get("attributes", {}).get("name", {}).get("en")
                if tag_name:
                    tags.append(tag_name)
            status_raw = (attrs.get("status") or "unknown").lower()
            return {
                "id": manga_id,
                "title": title,
                "cover_url": cover_url,
                "authors": authors,
                "artists": artists,
                "status": status_raw.title(),
                "year": attrs.get("year"),
                "last_volume": attrs.get("lastVolume"),
                "last_chapter": attrs.get("lastChapter"),
                "tags": tags[:10],
            }
        except Exception as e:
            logger.error(f"get_manga_info: {e}")
            return None

    async def get_latest_chapters(self, offset: int = 0) -> List[Dict]:
        try:
            params = {
                "limit": 20,
                "offset": offset,
                "translatedLanguage[]": ["en"],
                "order[publishAt]": "desc",
                "includes[]": ["manga", "scanlation_group"],
                "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
            }
            data = await self.api_request("/chapter", params)
            if not data or not data.get("data"):
                return []
            chapters = []
            for item in data["data"]:
                attrs = item.get("attributes", {})
                manga_id, manga_title, group = None, "Unknown", "Unknown"
                for rel in item.get("relationships", []):
                    if rel["type"] == "manga":
                        manga_id = rel["id"]
                        t = (rel.get("attributes") or {}).get("title") or {}
                        manga_title = t.get("en") or next(iter(t.values()), "Unknown") if t else "Unknown"
                    elif rel["type"] == "scanlation_group":
                        group = (rel.get("attributes") or {}).get("name") or "Unknown"
                if not manga_id:
                    continue
                chapters.append({
                    "id": item["id"],
                    "manga_id": manga_id,
                    "manga_title": manga_title,
                    "number": attrs.get("chapter") or "0",
                    "chapter": attrs.get("chapter") or "0",
                    "title": attrs.get("title") or "",
                    "url": item["id"],
                    "group": group,
                    "source": "mangadex",
                })
            return chapters
        except Exception as e:
            logger.error(f"get_latest_chapters: {e}")
            return []

    async def search_manga(self, query: str, limit: int = 25) -> List[Dict]:
        try:
            params = {
                "title": query,
                "limit": min(int(limit or 25), 100),
                "order[relevance]": "desc",
                "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
                "includes[]": ["cover_art"],
            }
            data = await self.api_request("/manga", params)
            if not data or not data.get("data"):
                return []
            results = []
            for item in data["data"]:
                attrs = item.get("attributes", {})
                title_obj = attrs.get("title", {}) or {}
                title = title_obj.get("en") or next(iter(title_obj.values()), "Unknown")
                results.append({
                    "id": item["id"],
                    "title": title,
                    "status": attrs.get("status"),
                    "year": attrs.get("year"),
                })
            return results
        except Exception as e:
            logger.error(f"search_manga: {e}")
            return []

    async def get_manga_chapters(self, manga_id: str, limit: int = 20, offset: int = 0, languages=None):
        if languages is None:
            languages = ["en"]
        try:
            params = {
                "manga": manga_id,
                "limit": limit,
                "offset": offset,
                "translatedLanguage[]": languages,
                "order[chapter]": "asc",
                "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
            }
            data = await self.api_request("/chapter", params)
            if data is None:
                return None
            items = data.get("data")
            if not items:
                return []
            chapters = []
            for item in items:
                attrs = item.get("attributes", {})
                chapters.append({
                    "id": item["id"],
                    "chapter": attrs.get("chapter") or "0",
                    "title": attrs.get("title") or "",
                    "number": attrs.get("chapter") or "0",
                })
            return chapters
        except Exception as e:
            logger.error(f"get_manga_chapters: {e}")
            return None

    async def get_chapter_images(self, chapter_id: str) -> List[str]:
        """Resolve page URLs via MangaDex at-home. Retries + data-saver fallback."""
        chapter_id = str(chapter_id).strip()
        if not chapter_id:
            return []

        for force443 in (True, False):
            for attempt in range(3):
                try:
                    params = {}
                    if force443:
                        params["forcePort443"] = "true"
                    data = await self.api_request(f"/at-home/server/{chapter_id}", params or None)
                    if not data:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    if data.get("result") != "ok":
                        logger.error(f"at-home result={data.get('result')} ch={chapter_id}")
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue

                    base = (data.get("baseUrl") or "").rstrip("/")
                    ch = data.get("chapter") or {}
                    hash_ = ch.get("hash")
                    # Prefer full quality, fall back to data-saver
                    files = ch.get("data") or []
                    quality = "data"
                    if not files:
                        files = ch.get("dataSaver") or []
                        quality = "data-saver"
                    if not base or not hash_ or not files:
                        logger.error(
                            f"at-home incomplete ch={chapter_id} base={bool(base)} hash={bool(hash_)} files={len(files) if files else 0}"
                        )
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue

                    urls = [f"{base}/{quality}/{hash_}/{f}" for f in files]
                    logger.info(f"get_chapter_images: {len(urls)} pages for {chapter_id} ({quality})")
                    return urls
                except Exception as e:
                    logger.error(f"get_chapter_images attempt={attempt}: {e}")
                    await asyncio.sleep(1.5 * (attempt + 1))

        logger.error(f"get_chapter_images gave up: {chapter_id}")
        return []
