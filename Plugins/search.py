# Manga-DL — Asa Bot
import logging
import secrets
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

logger = logging.getLogger(__name__)
chapter_tokens = {}

async def _fetch_all_chapters(api, manga_id, status_msg=None, page_size=50, max_pages=100):
    all_chapters = []
    offset = 0
    for _ in range(max_pages):
        batch = None
        for attempt in range(4):
            try:
                batch = await api.get_manga_chapters(manga_id, limit=page_size, offset=offset)
            except Exception as e:
                logger.error(f"fetch offset={offset}: {e}")
                batch = None
            if batch is not None:
                break
            await asyncio.sleep(1.5 * (attempt + 1))
        if batch is None:
            break
        if not batch:
            break
        all_chapters.extend(batch)
        if status_msg:
            try:
                await status_msg.edit_text(
                    f"🔍 Found <b>{len(all_chapters)}</b> chapters so far...",
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception:
                pass
        if len(batch) < page_size:
            break
        offset += page_size
        await asyncio.sleep(0.75)
    return all_chapters

def _token_for(source, manga_id, chapter_id):
    token = secrets.token_hex(5)
    chapter_tokens[token] = (source, manga_id, chapter_id)
    return token

def get_api_class(source):
    source = (source or "mangadex").lower()
    try:
        if source == "mangadex":
            from Plugins.Sites.mangadex import MangaDexAPI
            return MangaDexAPI
        if source == "webcentral":
            from Plugins.Sites.webcentral import WebCentralAPI
            return WebCentralAPI
        if source == "mangaforest":
            from Plugins.Sites.mangaforest import MangaForestAPI
            return MangaForestAPI
        if source == "mangakakalot":
            from Plugins.Sites.mangakakalot import MangakakalotAPI
            return MangakakalotAPI
        if source == "allmanga":
            from Plugins.Sites.allmanga import AllMangaAPI
            return AllMangaAPI
    except Exception as e:
        logger.error(f"get_api_class: {e}")
    return None

@Client.on_message(filters.command("search") & filters.private)
async def search_cmd(client, message):
    if len(message.command) < 2:
        await message.reply("Usage: <code>/search one piece</code>", parse_mode=enums.ParseMode.HTML)
        return
    query = " ".join(message.command[1:]).strip()
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("MangaDex", callback_data=f"src_mangadex_{query[:40]}")],
        [InlineKeyboardButton("MangaKakalot", callback_data=f"src_mangakakalot_{query[:40]}")],
    ])
    await message.reply(f"🔍 Search <b>{query}</b> — pick a source:", reply_markup=buttons, parse_mode=enums.ParseMode.HTML)

@Client.on_callback_query(filters.regex(r"^src_"))
async def source_search_cb(client, callback_query):
    data = callback_query.data[4:]
    for src in ("mangadex", "mangakakalot", "mangaforest", "allmanga", "webcentral"):
        if data.startswith(src + "_"):
            source, query = src, data[len(src)+1:]
            break
    else:
        await callback_query.answer("Invalid", show_alert=True)
        return
    await callback_query.answer()
    api_cls = get_api_class(source)
    if not api_cls:
        await callback_query.message.edit_text(f"❌ Source {source} unavailable")
        return
    await callback_query.message.edit_text(f"🔍 Searching <b>{query}</b>...", parse_mode=enums.ParseMode.HTML)
    try:
        async with api_cls(Config) as api:
            results = await api.search_manga(query, limit=25)
    except Exception as e:
        await callback_query.message.edit_text(f"❌ {e}")
        return
    if not results:
        await callback_query.message.edit_text("No results.")
        return
    buttons = [[InlineKeyboardButton((m.get("title") or "?")[:60], callback_data=f"view_{source}_{m['id']}")] for m in results[:25]]
    buttons.append([InlineKeyboardButton("⬅ Close", callback_data="stats_close")])
    await callback_query.message.edit_text(
        f"📖 Results ({len(results)}):",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML,
    )

@Client.on_callback_query(filters.regex(r"^view_"))
async def view_manga_cb(client, callback_query):
    parts = callback_query.data.split("_", 2)
    source, manga_id = parts[1], parts[2]
    await callback_query.answer()
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇ download chapters", callback_data=f"chapters_{source}_{manga_id}_0")],
        [InlineKeyboardButton("⬇⬇ DOWNLOAD ALL", callback_data=f"dl_all_{source}_{manga_id}")],
        [InlineKeyboardButton("⬅ Close", callback_data="stats_close")],
    ])
    await callback_query.message.edit_text(
        f"Source: <code>{source}</code>\nID: <code>{manga_id}</code>",
        reply_markup=buttons,
        parse_mode=enums.ParseMode.HTML,
    )

@Client.on_callback_query(filters.regex(r"^chapters_"))
async def chapters_cb(client, callback_query):
    raw = callback_query.data[len("chapters_"):]
    left, offset_s = raw.rsplit("_", 1)
    offset = int(offset_s)
    source = manga_id = None
    for src in ("mangadex", "mangakakalot", "mangaforest", "allmanga", "webcentral"):
        if left.startswith(src + "_"):
            source, manga_id = src, left[len(src)+1:]
            break
    await callback_query.answer()
    api_cls = get_api_class(source)
    async with api_cls(Config) as api:
        chapters = await api.get_manga_chapters(manga_id, limit=20, offset=offset)
    if chapters is None:
        await callback_query.answer("API error", show_alert=True)
        return
    if not chapters and offset == 0:
        await callback_query.message.edit_text("No chapters.")
        return
    rows, row = [], []
    for ch in chapters:
        num = ch.get("chapter") or ch.get("number") or "?"
        token = _token_for(source, manga_id, ch["id"])
        row.append(InlineKeyboardButton(f"ch {num}", callback_data=f"dl_ask_{token}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    nav = []
    if offset >= 20:
        nav.append(InlineKeyboardButton("⬅ prev", callback_data=f"chapters_{source}_{manga_id}_{offset-20}"))
    if chapters and len(chapters) >= 20:
        nav.append(InlineKeyboardButton("next ➡", callback_data=f"chapters_{source}_{manga_id}_{offset+20}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("⬇⬇ DOWNLOAD ALL", callback_data=f"dl_all_{source}_{manga_id}")])
    rows.append([InlineKeyboardButton("⬅ Close", callback_data="stats_close")])
    await callback_query.message.edit_text(
        f"<b>select chapter</b>\npage: {int(offset/20)+1}",
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode=enums.ParseMode.HTML,
    )

@Client.on_callback_query(filters.regex(r"^dl_ask_"))
async def dl_ask_cb(client, callback_query):
    token = callback_query.data[len("dl_ask_"):]
    ctx = chapter_tokens.pop(token, None)
    if not ctx:
        await callback_query.answer("Expired", show_alert=True)
        return
    source, manga_id, chapter_id = ctx
    await callback_query.answer("Downloading...")
    bot = getattr(client, "bot_instance", None)
    if not bot:
        await callback_query.message.reply("Bot not ready")
        return
    api_cls = get_api_class(source)
    manga_title, ch_num, ch_title = "Unknown", "0", ""
    try:
        async with api_cls(Config) as api:
            info = await api.get_manga_info(manga_id)
            if info:
                manga_title = info.get("title") or manga_title
    except Exception:
        pass
    chapter = {
        "id": chapter_id, "manga_id": manga_id, "manga_title": manga_title,
        "number": ch_num, "chapter": ch_num, "title": ch_title,
        "url": chapter_id, "source": source, "group": "Unknown",
    }
    status = await callback_query.message.reply(f"⬇️ Ch {ch_num} — {manga_title}")
    ok = await bot.process_chapter(chapter)
    await status.edit_text("✅ Done" if ok else "⚠️ Issues")

@Client.on_callback_query(filters.regex(r"^dl_all_"))
async def dl_all_cb(client, callback_query):
    parts = callback_query.data.split("_", 2)
    rest = parts[2]
    source, manga_id = rest.split("_", 1)
    await callback_query.answer("Queuing ALL...")
    bot = getattr(client, "bot_instance", None)
    api_cls = get_api_class(source)
    status = await callback_query.message.reply("🔍 Fetching all chapters...")
    manga_title = "Unknown"
    async with api_cls(Config) as api:
        try:
            info = await api.get_manga_info(manga_id)
            if info:
                manga_title = info.get("title") or manga_title
        except Exception:
            pass
        all_chapters = await _fetch_all_chapters(api, manga_id, status_msg=status)
    seen, uniq = set(), []
    for ch in all_chapters:
        if ch.get("id") and ch["id"] not in seen:
            seen.add(ch["id"])
            uniq.append(ch)
    if not uniq:
        await status.edit_text("No chapters")
        return
    await status.edit_text(f"⏳ Downloading <b>{len(uniq)}</b> — {manga_title}", parse_mode=enums.ParseMode.HTML)
    ok_n = 0
    for i, ch in enumerate(uniq, 1):
        ch_num = ch.get("chapter") or ch.get("number") or "0"
        chapter = {
            "id": ch["id"], "manga_id": manga_id, "manga_title": manga_title,
            "number": ch_num, "chapter": ch_num, "title": ch.get("title") or "",
            "url": ch["id"], "source": source, "group": "Unknown",
        }
        try:
            if await bot.process_chapter(chapter):
                ok_n += 1
        except Exception as e:
            logger.error(f"dl_all: {e}")
        if i % 3 == 0:
            try:
                await status.edit_text(f"⏳ {i}/{len(uniq)} OK:{ok_n}")
            except Exception:
                pass
        await asyncio.sleep(2)
    await status.edit_text(f"✅ Done {ok_n}/{len(uniq)} — {manga_title}")

async def custom_dl_input_handler(client, message, user_id, state_data):
    from Plugins.helper import user_states
    text = (message.text or "").strip()
    source, manga_id = state_data.get("source"), state_data.get("manga_id")
    user_states.pop(user_id, None)
    await message.reply("Use chapter buttons or DOWNLOAD ALL for now.")
