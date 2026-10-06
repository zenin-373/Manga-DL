"""Clean WeebCentral chapter list (no Last Read / ISO in title)."""
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://weebcentral.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": BASE_URL,
}

def scrape_chapter_list(series_url: str) -> list:
    match = re.search(r"/series/([^/]+)/", series_url)
    if not match:
        raise ValueError(f"Could not extract series ID from URL: {series_url}")
    series_id = match.group(1)
    full_ch_url = f"{BASE_URL}/series/{series_id}/full-chapter-list"
    print(f"Fetching chapter list: {full_ch_url}")
    res = requests.get(full_ch_url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "lxml")
    chapter_links = soup.select("div[x-data] > a[href*='/chapters/']")
    if not chapter_links:
        chapter_links = soup.select("a[href*='/chapters/']")
    chapter_links = list(reversed(chapter_links))
    chapters = []
    for index, a in enumerate(chapter_links, start=1):
        href = a.get("href") or ""
        chapter_url = BASE_URL + href if href.startswith("/") else href
        name_el = a.select_one("span.grow > span")
        ch_text = name_el.get_text(strip=True) if name_el else a.get_text(separator=" ", strip=True)
        ch_text = re.sub(r"\s*Last Read\s*", " ", ch_text, flags=re.I)
        ch_text = re.sub(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z?", "", ch_text)
        ch_text = re.sub(r"\s+", " ", ch_text).strip() or f"Chapter {index}"
        date_tag = a.find("time")
        date_str = "Unknown"
        if date_tag is not None:
            date_str = (date_tag.get("datetime") or date_tag.get_text(strip=True) or "Unknown")
            if "T" in str(date_str):
                date_str = str(date_str).split("T")[0]
        mnum = re.search(r"(?i)(?:chapter|ch\.?|ep\.?|episode)\s*([0-9]+(?:\.[0-9]+)?)", ch_text)
        number = mnum.group(1) if mnum else str(index)
        chapters.append({
            "index": index,
            "title": ch_text,
            "number": number,
            "url": chapter_url,
            "date": date_str,
        })
    print(f"\nTotal chapters: {len(chapters)}")
    if chapters:
        print(f"   Ch 1: {chapters[0]['title']}")
        print(f"   Ch {len(chapters)}: {chapters[-1]['title']}")
    return chapters
