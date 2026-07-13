#!/usr/bin/env python3
"""Fetch news from Telegram channels and RSS feeds, save as news.json"""

import json
import re
import time
from datetime import datetime, timezone, timedelta
from collections import OrderedDict
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

import fetch_youtube

TELEGRAM_CHANNELS = [
    "PressTV",
    "suppressednews",
]

RSS_FEEDS = [
    {"name": "MiddleEastMonitor", "url": "https://www.middleeastmonitor.com/feed/"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
ARABIC_TZ = timezone(timedelta(hours=3))
OUTPUT_FILE = "news.json"
MAX_ITEMS = 150
HOURS_WINDOW = 72
YT_WINDOW = 24  # مدة ظهور فيديوهات يوتيوب في أعلى الصفحة (بالساعات) ثم تختفي

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_translator = GoogleTranslator(source="en", target="ar")
_translation_cache = {}


# ---------- Telegram parsing ----------

def parse_message(el):
    for part in el.find_all(["b", "i", "u", "s", "a", "code", "pre", "span", "br", "strong", "em"]):
        part.unwrap()
    txt = el.get_text(separator=" ", strip=True)
    txt = re.sub(r"\s+", " ", txt).strip()
    if len(txt) < 10:
        return None
    if txt.startswith("Forwarded from") and len(txt) < 50:
        return None
    if "window.matchMedia" in txt or "protoUrl" in txt or "TWallpaper" in txt:
        return None
    if txt.startswith("Telegram:") and ("Download" in txt or "View" in txt or "Contact" in txt):
        return None
    return txt


def parse_views(el):
    vm = el.select_one(".tgme_widget_message_views")
    if vm:
        v = vm.get_text(strip=True).replace(",", "").replace(".", "")
        try:
            return int(v)
        except Exception:
            pass
    reactions = el.select(".tgme_widget_message_reaction span")
    if reactions:
        total = 0
        for r in reactions:
            try:
                total += int(r.get_text(strip=True))
            except Exception:
                pass
        return total
    return 0


def parse_telegram_page(html, channel):
    soup = BeautifulSoup(html, "html.parser")
    messages = soup.select(".tgme_widget_message_wrap")
    items = []
    for msg in messages:
        text_el = msg.select_one(".tgme_widget_message_text, .js-message_text")
        if not text_el:
            continue
        text = parse_message(text_el)
        if not text:
            continue
        views = parse_views(msg)
        time_el = msg.select_one("time[datetime]")
        time_str = ""
        if time_el:
            dt = time_el.get("datetime", "")
            if len(dt) >= 16:
                time_str = dt[11:16]
        items.append(OrderedDict([
            ("channel", channel),
            ("text", text[:1200]),
            ("time", time_str),
            ("views", views),
            ("source", "telegram"),
        ]))
    return items


# ---------- RSS parsing ----------

def parse_rss(url, name):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"  RSS Error ({name}): {e}")
        return []

    items = []
    nodes = root.iter("item") if list(root.iter("item")) else root.iter("entry")
    for it in nodes:
        title = (it.findtext("title") or
                 it.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        if not title:
            continue
        pub = (it.findtext("pubDate") or
               it.findtext("published") or
               it.findtext("dc:date") or "")
        items.append(OrderedDict([
            ("channel", name),
            ("text", title[:1200]),
            ("time", ""),
            ("views", 0),
            ("pubDate", pub),
            ("source", "rss"),
        ]))
    print(f"  Got {len(items)} items from RSS {name}")
    return items


# ---------- Date assignment ----------

def assign_dates(items):
    now = datetime.now(ARABIC_TZ)
    current_date = now.date()
    last_hour = {}
    per_channel_dates = {}

    day_names = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    month_names = [
        "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
    ]

    for item in items:
        if item.get("source") == "rss":
            dt = parse_rss_date(item.get("pubDate", ""))
            if dt:
                d = dt.astimezone(ARABIC_TZ).date()
                t = dt.astimezone(ARABIC_TZ).strftime("%H:%M")
                item["date"] = f"{day_names[d.weekday()]} {d.day} {month_names[d.month]} {d.year}"
                item["sort_key"] = dt.astimezone(ARABIC_TZ).isoformat()
                item["time"] = t
            else:
                item["date"] = f"{day_names[now.weekday()]} {now.day} {month_names[now.month]} {now.year}"
                item["sort_key"] = now.isoformat()
            item.pop("pubDate", None)
            continue

        if item.get("source") == "youtube":
            continue

        ch = item["channel"]
        if ch not in last_hour:
            last_hour[ch] = 99
            per_channel_dates[ch] = now.date()

        t = item.get("time", "")
        h = 12
        if t:
            try:
                h = int(t[:2])
            except Exception:
                h = 12

        cd = per_channel_dates[ch]
        lh = last_hour[ch]
        if lh < 99 and h > 12 and lh < 6:
            cd -= timedelta(days=1)
        elif lh < 99 and h > lh + 4:
            cd -= timedelta(days=1)

        last_hour[ch] = h
        per_channel_dates[ch] = cd

        d = cd
        item["date"] = f"{day_names[d.weekday()]} {d.day} {month_names[d.month]} {d.year}"
        item["sort_key"] = datetime(d.year, d.month, d.day,
                                    int(t[:2]) if t else 12,
                                    int(t[3:5]) if t else 0,
                                    tzinfo=ARABIC_TZ).isoformat()

    return items


def parse_rss_date(s):
    if not s:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def parse_sort_key(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ARABIC_TZ)
    return dt


# ---------- Translation ----------

def is_arabic(text):
    return bool(_ARABIC_RE.search(text))


def translate_to_arabic(text):
    if text in _translation_cache:
        return _translation_cache[text]
    try:
        result = _translator.translate(text)
        _translation_cache[text] = result
        time.sleep(0.3)
        return result
    except Exception as e:
        print(f"  Translation error: {e}")
        _translation_cache[text] = text
        return text


def translate_english_items(items):
    count = 0
    for item in items:
        txt = item["text"]
        if not is_arabic(txt):
            ar = translate_to_arabic(txt)
            if ar and ar != txt:
                item["text"] = ar
                item["translated"] = True
                count += 1
    if count:
        print(f"  Translated {count} English items to Arabic")
    return items


# ---------- Main ----------

def load_existing():
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main():
    all_news = []
    seen = set()
    fetched_sources = set()

    for ch in TELEGRAM_CHANNELS:
        print(f"Fetching @{ch}...")
        try:
            resp = requests.get(f"https://t.me/s/{ch}", headers=HEADERS, timeout=30)
            resp.raise_for_status()
            items = parse_telegram_page(resp.text, ch)
            if not items:
                print("  No items returned")
                continue
            for item in items:
                key = f"{ch}:{item['text'][:80]}"
                if key not in seen:
                    seen.add(key)
                    all_news.append(item)
            fetched_sources.add(ch)
            print(f"  Got {len(items)} items")
        except Exception as e:
            print(f"  Error: {e}")

    for feed in RSS_FEEDS:
        print(f"Fetching RSS {feed['name']}...")
        items = parse_rss(feed["url"], feed["name"])
        if items:
            fetched_sources.add(feed["name"])
            for item in items:
                key = f"{feed['name']}:{item['text'][:80]}"
                if key not in seen:
                    seen.add(key)
                    all_news.append(item)

    try:
        yt_items = fetch_youtube.build_youtube_items()
        for item in yt_items:
            key = f"{item['channel']}:{item['link']}"
            if key not in seen:
                seen.add(key)
                all_news.append(item)
                fetched_sources.add(fetch_youtube.OUTPUT_CHANNEL)
    except Exception as e:
        print(f"  YouTube integration error: {e}")

    if not fetched_sources:
        print("All sources failed to fetch. Keeping existing news.json.")
        return

    existing = load_existing()
    for item in existing:
        ch = item.get("channel", "")
        if ch in (TELEGRAM_CHANNELS + [f["name"] for f in RSS_FEEDS]) and ch not in fetched_sources:
            key = f"{ch}:{item.get('text', '')[:80]}"
            if key not in seen:
                seen.add(key)
                all_news.append(item)
                print(f"  Kept existing items from {ch} (fetch failed)")

    all_news = assign_dates(all_news)

    now = datetime.now(ARABIC_TZ)
    cutoff = now - timedelta(hours=HOURS_WINDOW)
    yt_cutoff = now - timedelta(hours=YT_WINDOW)
    filtered = []
    youtube_top = []
    for item in all_news:
        if item.get("source") == "youtube":
            dt = parse_sort_key(item.get("sort_key", ""))
            if dt is not None and dt >= yt_cutoff:
                youtube_top.append(item)
            continue
        sk = item.get("sort_key", "")
        dt = parse_sort_key(sk)
        if dt is None:
            continue
        if dt >= cutoff:
            filtered.append(item)
    print(f"  Filtered to last {HOURS_WINDOW}h: {len(filtered)} of {len(all_news)} items")
    print(f"  YouTube (top, <{YT_WINDOW}h): {len(youtube_top)}")

    youtube_top.sort(key=lambda x: x.get("sort_key", ""), reverse=True)
    filtered.sort(key=lambda x: x.get("sort_key", ""), reverse=True)
    all_news = youtube_top + filtered
    all_news = all_news[:MAX_ITEMS]

    for item in all_news:
        item.pop("sort_key", None)
        item.pop("source", None)

    all_news = translate_english_items(all_news)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    print(f"Total: {len(all_news)} items saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
