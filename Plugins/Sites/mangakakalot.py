# Manga-DL — Asa Bot
class MangakakalotAPI:
    def __init__(self, Config):
        self.Config = Config
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        pass
    async def search_manga(self, query, limit=25):
        return []
    async def get_manga_info(self, manga_id):
        return None
    async def get_manga_chapters(self, *a, **k):
        return []
    async def get_chapter_images(self, *a, **k):
        return []
    async def get_latest_chapters(self, offset=0):
        return []
