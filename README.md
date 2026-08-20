# Manga-DL

Telegram bot to search, download, and post manga chapters (MangaDex and other sources).

**Owner:** [@Asa_Mikata373](https://t.me/Asa_Mikata373)

## Features

- Search manga and download single chapters, ranges, or all chapters
- PDF upload to Telegram dump / upload channels
- Optional Google Drive save (Colab mount path)
- Live Aeon-style progress status in Telegram
- MongoDB config (channels, monitoring, admins)
- One-click Heroku deploy via GitHub Actions form

## Quick start (local / Colab)

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

## Deploy to Heroku (GitHub Actions)

You can deploy **without** putting secrets in the repo. Use the **Run workflow** form.

1. Open **Actions** → **Deploy to Heroku** → **Run workflow**
2. Fill the form:

| Field | Required | Description |
|--------|----------|-------------|
| **Heroku App name** | Yes | New or existing Heroku app name |
| **Heroku API key** | Yes | [Account settings → API Key](https://dashboard.heroku.com/account) |
| **Heroku email address** | Yes | Your Heroku login email |
| **Heroku Team Name** | No | Only if the app is under a team |
| **Telegram bot token** | Yes | From [@BotFather](https://t.me/BotFather) |
| **Owner's telegram ID** | Yes | Your numeric Telegram user ID |
| **Telegram API ID** | Yes | From [my.telegram.org](https://my.telegram.org) |
| **Telegram API HASH** | Yes | From [my.telegram.org](https://my.telegram.org) |
| **MongoDB URL** | Yes | MongoDB Atlas (or other) connection URI |
| **MongoDB database name** | No | Default: `manga_bot` |

3. Click **Run workflow**

The job will:

- Create the Heroku app if it does not exist
- Set Config Vars from the form (`BOT_TOKEN`, `API_ID`, `API_HASH`, `USER_ID`, `DB_URL`, `DB_NAME`)
- Deploy this repo
- Scale the **worker** dyno (`python3 Bot.py`)

### Multiple bots

Run the workflow again with a **different Heroku app name** and a **different bot token** (and ideally a different `DB_NAME`). Each run deploys a separate bot.

### Notes

- Needs a **worker** dyno (not only web). Use Basic or higher for 24/7.
- Form values can appear in Actions logs — use a **private** repo if you paste real tokens.
- Google Drive mount is for Colab; on Heroku use `UPLOAD_MODE=telegram`.

## Commands

- `/start` — home
- `/search <name>` — search manga
- `/settings` — bot settings
- `/help` — help

## License

Use freely for your own bot. Branding: Powered By @Asa_Mikata373
