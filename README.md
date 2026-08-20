# Manga-DL

Telegram bot to search, download, and post manga chapters (MangaDex and other sources).

**Owner:** [@Asa_Mikata373](https://t.me/Asa_Mikata373)

## Features

- Search manga and download single chapters, ranges, or all chapters
- PDF upload to Telegram dump / upload channels
- Optional Google Drive save (Colab mount path)
- Live Aeon-style progress status in Telegram
- MongoDB config (channels, monitoring, admins)

## Quick start

```bash
git clone https://github.com/zenin-373/Manga-DL.git
cd Manga-DL
# edit config.py with BOT_TOKEN, API_ID, API_HASH, USER_ID, DB_URL
pip install -r requirements.txt
python3 Bot.py
```

## Config

Set in `config.py` or environment variables:

- `BOT_TOKEN`, `API_ID`, `API_HASH`, `USER_ID`
- `DB_URL`, `DB_NAME`
- Optional: `DRIVE_MOUNT_PATH`, `UPLOAD_MODE`

## Commands

- `/start` — home
- `/search <name>` — search manga
- `/settings` — bot settings
- `/help` — help

## License

Use freely for your own bot. Branding: Powered By @Asa_Mikata373
