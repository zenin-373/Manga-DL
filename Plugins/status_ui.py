# Manga-DL — Asa Bot
"""Live status messages for manga download/upload."""
import time
import logging
from pyrogram import enums

logger = logging.getLogger(__name__)
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]


def get_readable_file_size(size_in_bytes):
    try:
        size_in_bytes = float(size_in_bytes or 0)
    except Exception:
        return "0B"
    if size_in_bytes <= 0:
        return "0B"
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"


def get_readable_time(seconds):
    try:
        seconds = int(max(0, float(seconds)))
    except Exception:
        return "-"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h{m}m"
    if m:
        return f"{m}m{s}s"
    return f"{s}s"


def get_progress_bar_string(pct):
    try:
        if isinstance(pct, str):
            pct = float(pct.strip().replace("%", ""))
        p = min(max(float(pct), 0), 100)
    except Exception:
        p = 0
    c_full = int((p + 5) // 10)
    return "●" * c_full + "○" * (10 - c_full)


def format_status(name, status, percent=0, processed=None, total=None, speed=None, eta=None, extra=None):
    """Old-style status — no Powered By line."""
    lines = [
        f"<b>{status}:</b> <code>{_esc(name)}</code>",
        f"{get_progress_bar_string(percent)} {percent:.1f}%",
    ]
    if processed is not None or total is not None:
        if isinstance(processed, (int, float)) and isinstance(total, (int, float)) and total > 50:
            lines.append(
                f"<b>Processed:</b> {get_readable_file_size(processed)}"
                f" of {get_readable_file_size(total)}"
            )
        else:
            lines.append(f"<b>Count:</b> {processed or 0}/{total or '?'}")
    if speed:
        lines.append(f"<b>Speed:</b> {speed}")
    if eta:
        lines.append(f"<b>ETA:</b> {eta}")
    if extra:
        lines.append(extra)
    return "\n".join(lines)


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class TaskStatus:
    def __init__(self, app, chat_id, min_interval=2.5):
        self.app = app
        self.chat_id = chat_id
        self.min_interval = min_interval
        self.message = None
        self._last_edit = 0.0
        self.name = ""
        self.status = "Queued"
        self.percent = 0.0
        self.processed = 0
        self.total = 0
        self.speed = None
        self.eta = None
        self._t0 = time.time()
        self._last_processed = 0
        self._last_t = self._t0

    async def start(self, name, status="Download"):
        self.name = name
        self.status = status
        self._t0 = time.time()
        try:
            self.message = await self.app.send_message(
                self.chat_id,
                format_status(name, status, 0, 0, 0),
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"TaskStatus.start: {e}")
            self.message = None

    async def update(self, status=None, current=None, total=None, percent=None, force=False, extra=None):
        if status:
            self.status = status
        if current is not None:
            self.processed = current
        if total is not None:
            self.total = total
        if percent is not None:
            self.percent = percent
        elif self.total:
            self.percent = min(100.0, 100.0 * float(self.processed) / float(self.total))

        now = time.time()
        dt = now - self._last_t
        if dt > 0.5 and current is not None:
            delta = max(0, (current or 0) - self._last_processed)
            rate = delta / dt
            if self.total and self.total > 50:
                self.speed = f"{get_readable_file_size(rate)}/s"
            else:
                self.speed = f"{rate:.1f}/s"
            left = max(0, (self.total or 0) - (current or 0))
            self.eta = get_readable_time(left / rate) if rate > 0 else "-"
            self._last_processed = current or 0
            self._last_t = now

        if not force and (now - self._last_edit) < self.min_interval:
            return
        self._last_edit = now
        if not self.message:
            return
        try:
            await self.message.edit_text(
                format_status(
                    self.name, self.status, self.percent,
                    self.processed, self.total, self.speed, self.eta, extra,
                ),
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                logger.debug(f"TaskStatus.update: {e}")

    async def finish(self, ok=True, detail=""):
        elapsed = get_readable_time(time.time() - self._t0)
        status = "Completed" if ok else "Failed"
        if ok:
            self.percent = 100.0
        extra = f"<b>Time:</b> {elapsed}"
        if detail:
            extra += f"\n{detail}"
        if not self.message:
            return
        try:
            await self.message.edit_text(
                format_status(
                    self.name, status, self.percent,
                    self.processed, self.total, None, None, extra,
                ),
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.debug(f"TaskStatus.finish: {e}")
