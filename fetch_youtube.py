#!/usr/bin/env python3
"""Fetch new videos from a YouTube channel via its public RSS feed and produce news items.

Uses the official YouTube RSS feed (no auth, works from server IPs) instead of
scraping, which YouTube blocks ("Sign in to confirm you're not a bot") from
datacenter IPs such as GitHub Actions runners.
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET

import requests
from youtube_transcript_api import YouTubeTranscriptApi

CHANNEL_ID = "UCcoRLj9MmvA-YjAkJqyt8Tw"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
OUTPUT_CHANNEL = "YouTube-AlAouni"
CACHE_FILE = "youtube_cache.json"
MAX_VIDEOS = 15
ARABIC_TZ = timezone(timedelta(hours=3))

# LLM summarization (OpenAI-compatible). Enable by setting these env vars:
#   LLM_BASE_URL  e.g. https://models.inference.ai.azure.com   (GitHub Models)
#                 or   https://generativelanguage.googleapis.com/v1beta/openai  (Gemini)
#   LLM_API_KEY   the API key / token
#   LLM_MODEL     e.g. gpt-4o-mini (GitHub Models) or gemini-2.5-flash (Gemini)
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").strip()
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini").strip()

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}

DAY_NAMES = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
MONTH_NAMES = [
    "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]


def get_latest_videos(n=MAX_VIDEOS):
    try:
        r = requests.get(RSS_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  RSS fetch failed: {e}")
        return []
    try:
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"  RSS parse failed: {e}")
        return []
    out = []
    for entry in root.findall("atom:entry", _NS):
        vid = entry.findtext("yt:videoId", namespaces=_NS)
        title = (entry.findtext("atom:title", namespaces=_NS) or "").strip()
        link = entry.find("atom:link", namespaces=_NS)
        href = link.get("href") if link is not None else ""
        published = entry.findtext("atom:published", namespaces=_NS) or ""
        if not vid:
            continue
        upload_date = ""
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", published)
        if m:
            upload_date = m.group(1) + m.group(2) + m.group(3)
        out.append({
            "id": vid,
            "title": title,
            "view_count": 0,
            "upload_date": upload_date,
            "link": href,
        })
        if len(out) >= n:
            break
    return out


def get_transcript(video_id):
    try:
        t = YouTubeTranscriptApi().fetch(video_id, languages=["ar", "en"])
        return " ".join(s.text for s in t)
    except Exception as e:
        print(f"  Transcript error ({video_id}): {e}")
        return None


def summarize_video(title, transcript):
    """Summarize an Arabic transcript into a short Arabic summary via an
    OpenAI-compatible endpoint. Returns None if not configured or on error."""
    if not LLM_BASE_URL or not LLM_API_KEY:
        return None
    if not transcript:
        return None
    text = transcript[:6000]
    system = (
        "أنت محرر أخبار. لخّص النص التالي (ترجمة تلقائية قد تخلو من علامات الترقيم) "
        "في ٢ إلى ٤ جمل عربية واضحة وموضوعية تلخّص محتوى الفيديو دون إضافة أي معلومة "
        "غير مذكورة. ابدأ بجملة عنوان قصيرة إن أمكن."
    )
    user = f"عنوان الفيديو: {title}\n\nنص الفيديو:\n{text}"
    try:
        r = requests.post(
            LLM_BASE_URL.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": LLM_MODEL, "temperature": 0.2,
                  "messages": [
                      {"role": "system", "content": system},
                      {"role": "user", "content": user},
                  ]},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        summary = data["choices"][0]["message"]["content"].strip()
        return summary or None
    except Exception as e:
        print(f"  Summarization error ({title[:40]}): {e}")
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
        print(f"  Got {len(videos)} latest videos from YouTube RSS")
    except Exception as e:
        print(f"  YouTube RSS error: {e}")
        videos = []

    for v in videos:
        vid = v["id"]
        if vid in cache:
            continue
        url = v.get("link") or f"https://www.youtube.com/watch?v={vid}"
        transcript = get_transcript(vid)
        summary = summarize_video(v["title"], transcript) if transcript else None
        cache[vid] = {
            "title": v["title"],
            "url": url,
            "views": v.get("view_count", 0),
            "upload_date": v.get("upload_date", ""),
            "has_transcript": bool(transcript),
            "summary": summary,
        }
        print(f"  New video cached: {vid}" + (" (summarized)" if summary else ""))

    save_cache(cache)

    cache = {vid: data for vid, data in cache.items()
             if (_date_from_upload(data.get("upload_date", "")) or now) >= now - timedelta(days=60)}
    save_cache(cache)

    llm_ready = bool(LLM_BASE_URL and LLM_API_KEY)
    items = []
    for vid, data in cache.items():
        if llm_ready and not data.get("summary") and data.get("has_transcript"):
            transcript = get_transcript(vid)
            if transcript:
                data["summary"] = summarize_video(data.get("title", ""), transcript)
                save_cache(cache)
        d = _date_from_upload(data.get("upload_date", "")) or now
        date_str = f"{DAY_NAMES[d.weekday()]} {d.day} {MONTH_NAMES[d.month]} {d.year}"
        items.append({
            "channel": OUTPUT_CHANNEL,
            "text": data.get("summary") or data.get("title", ""),
            "link": data.get("url", ""),
            "views": data.get("views", 0),
            "time": "",
            "date": date_str,
            "sort_key": d.isoformat(),
            "source": "youtube",
        })

    items.sort(key=lambda x: x.get("sort_key", ""), reverse=True)
    print(f"  YouTube items: {len(items)}")
    return items
