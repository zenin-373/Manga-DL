"""Lookup official/licensed chapter titles via kulaid/manga-chapter-titles JSON data.

https://github.com/kulaid/manga-chapter-titles
"""
from __future__ import annotations

import json
import re
import urllib.request
from functools import lru_cache
from typing import Dict, Optional

DATA_BASE = "https://raw.githubusercontent.com/kulaid/manga-chapter-titles/master/data"


def match_key(name: str) -> str:
    """Same idea as chaptertitles.MatchKey — lowercase alphanumerics, drop lone x."""
    s = name.lower()
    s = re.sub(r"\(.*?\)", "", s)  # strip (Color), (Official Colored), etc.
    s = re.sub(r"[^a-z0-9]+", "", s)
    s = s.replace("x", "") if False else s  # keep x inside words; dataset drops standalone x
    # drop standalone x between letters already removed by non-alnum strip
    return s


@lru_cache(maxsize=1)
def _load_index() -> list:
    with urllib.request.urlopen(f"{DATA_BASE}/index.json", timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data.get("series") or []


@lru_cache(maxsize=32)
def _load_series_file(filename: str) -> dict:
    with urllib.request.urlopen(f"{DATA_BASE}/{filename}", timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def resolve_series(title: str) -> Optional[dict]:
    """Find index row for a manga title (fuzzy match_key)."""
    key = match_key(title)
    if not key:
        return None
    best = None
    for row in _load_index():
        mk = row.get("match_key") or match_key(row.get("series") or "")
        if mk == key:
            return row
        # partial: deathnote in deathnotecolor
        if key.startswith(mk) or mk.startswith(key):
            if best is None or len(mk) > len(best.get("match_key") or ""):
                best = row
    return best


def get_chapter_title(manga_title: str, chapter_num) -> Optional[str]:
    """Return official title for chapter number, or None."""
    row = resolve_series(manga_title)
    if not row:
        return None
    data = _load_series_file(row["file"])
    chapters: Dict[str, str] = data.get("chapters") or {}
    # normalize number key: 4, 4.0, "4", "04" → "4"
    try:
        n = float(chapter_num)
        if n == int(n):
            key = str(int(n))
        else:
            key = str(n).rstrip("0").rstrip(".") if "." in str(n) else str(n)
    except (TypeError, ValueError):
        key = str(chapter_num).strip()
    title = chapters.get(key)
    if title:
        return title.strip()
    # try alternate string forms
    for k, v in chapters.items():
        try:
            if float(k) == float(key):
                return v.strip()
        except ValueError:
            continue
    return None


def enrich_chapter_title(manga_title: str, chapter_num, fallback: str = "") -> str:
    """Prefer dataset title; else cleaned fallback; else empty."""
    t = get_chapter_title(manga_title, chapter_num)
    if t:
        return t
    fb = (fallback or "").strip()
    # ignore generic "Chapter N"
    if re.fullmatch(r"(?i)chapter\s*\d+(\.\d+)?", fb):
        return ""
    return fb
