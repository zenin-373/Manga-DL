# Manga-DL — Asa Bot
from aiohttp import web

async def web_server():
    async def index(request):
        return web.Response(text="Manga-DL / Asa Bot is running")
    app = web.Application()
    app.router.add_get("/", index)
    return app
