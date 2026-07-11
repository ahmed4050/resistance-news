#!/usr/bin/env python3
"""Fetch new videos from a YouTube channel and produce news items for the site."""

import json
from datetime import datetime, timezone, timedelta

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

CHANNEL_URL = "https://www.youtube.com/@%D8%B9%D8%A8%D8%AF%D8%A7%D9%84%D8%AD%D9%85%D9%8A%D8%AF%D8%A7%D9%84%D8%B9%D9%88%D9%86%D9%8A"
OUTPUT_CHANNEL = "YouTube-AlAouni"
CACHE_FILE = "youtube_cache.json"
MAX_VIDEOS = 15
HOURS_WINDOW = 72
ARABIC_TZ = timezone(timedelta(hours=3))

DAY_NAMES = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
MONTH_NAMES = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]


def get_latest_videos(n=MAX_VIDEOS):
    opts = {"quiet": True, "extract_flat": "playlist", "playlistend": n}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
        out = []
        for e in info.get("entries", []):
            if not e.get("id"):
                continue
            out.append({
                "id": e["id"],
                "title": e.get("title") or "",
                "view_count": e.get("view_count") or 0,
                "upload_date": e.get("upload_date") or "",
            })
        return out


def get_transcript(video_id):
    try:
        t = YouTubeTranscriptApi().fetch(video_id, languages=["ar", "en"])
        return " ".join(s.text for s in t)
    except Exception as e:
        print(f"  Transcript error ({video_id}): {e}")
        return None


def _date_from_upload(upload_date):
    if upload_date and len(upload_date) == 8:
        try:
            return datetime(
                int(upload_date[:4]), int(upload_date[4:6]),
                int(upload_date[6:8]), tzinfo=ARABIC_TZ,
            )
        except Exception:
            return None
    return None


def load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def build_youtube_items():
    cache = load_cache()
    now = datetime.now(ARABIC_TZ)

    try:
        videos = get_latest_videos()
        print(f"  Got {len(videos)} latest videos from YouTube channel")
    except Exception as e:
        print(f"  YouTube fetch failed: {e}")
        videos = []

    for v in videos:
        vid = v["id"]
        if vid in cache:
            continue
        url = f"https://www.youtube.com/watch?v={vid}"
        d = _date_from_upload(v["upload_date"]) or now
        transcript = get_transcript(vid)
        cache[vid] = {
            "title": v["title"],
            "url": url,
            "views": v.get("view_count", 0),
            "upload_date": v.get("upload_date", ""),
            "has_transcript": bool(transcript),
        }
        print(f"  New video cached: {vid} - {v['title'][:60].encode('ascii','replace').decode()}")

    save_cache(cache)

    items = []
    for vid, data in cache.items():
        d = _date_from_upload(data.get("upload_date", "")) or now
        if d < now - timedelta(hours=HOURS_WINDOW):
            continue
        date_str = f"{DAY_NAMES[d.weekday()]} {d.day} {MONTH_NAMES[d.month]} {d.year}"
        items.append({
            "channel": OUTPUT_CHANNEL,
            "text": data.get("title", ""),
            "link": data.get("url", ""),
            "views": data.get("views", 0),
            "time": "",
            "date": date_str,
            "sort_key": d.isoformat(),
            "source": "youtube",
        })

    items.sort(key=lambda x: x.get("sort_key", ""), reverse=True)
    print(f"  YouTube items in window: {len(items)}")
    return items
