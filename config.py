# Manga-DL — Asa Bot
import os

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    USER_ID = int(os.getenv("USER_ID") or "0")
    API_ID = int(os.getenv("API_ID") or "0")
    API_HASH = os.getenv("API_HASH", "")
    DB_NAME = os.getenv("DB_NAME", "manga_bot")
    DB_URL = os.getenv("DB_URL", "")
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL") or "300")
    MAX_CHAPTERS_PER_CHECK = int(os.getenv("MAX_CHAPTERS") or "5")
    DOWNLOAD_DIR = "downloads"
    STATE_FILE = "bot_state.json"
    CACHE_FILE = "manga_ids_cache.json"
    API_BASE = "https://api.mangadex.org"
    WEB_BASE = "https://mangadex.org"
    LOOKBACK_HOURS = 24
    MAX_IMAGE_SIZE = 10 * 1024 * 1024
    MAX_PDF_SIZE = 50 * 1024 * 1024
    USE_DATABASE = os.getenv("USE_DATABASE", "True").lower() == "True"

    PORT = int(os.getenv("PORT") or "8080")
    TG_BOT_WORKERS = int(os.getenv("TG_BOT_WORKERS") or "4")

    PICS = [
        "https://ibb.co/8gBTKm9R",
        "https://ibb.co/LD55GVZm",
        "https://ibb.co/27HZcLrB",
        "https://ibb.co/CsMGTdvp",
        "https://ibb.co/9d5Wnf1",
        "https://ibb.co/JwmM4MJH",
        "https://ibb.co/27dPPLj1",
        "https://ibb.co/DHp5wXMG",
        "https://ibb.co/YBJTHrcM",
        "https://ibb.co/xSbg9GKZ",
        "https://ibb.co/cctdJTKT",
        "https://ibb.co/Lz2HkVHm",
    ]

    DEFAULT_FILENAME_FORMAT = "{manga_name} [Ch-{chapter}]"

    DRIVE_MOUNT_PATH = os.getenv("DRIVE_MOUNT_PATH", "")
    UPLOAD_MODE = os.getenv("UPLOAD_MODE", "both")
