#!/usr/bin/env python3
"""Fetch news from Telegram channels and save as news.json"""

import json
import re
from datetime import datetime, timezone, timedelta
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup

CHANNELS = [
    "hezbulla",
    "PalestineResist",
    "libanon_news",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
ARABIC_TZ = timezone(timedelta(hours=3))
OUTPUT_FILE = "news.json"
MAX_ITEMS = 150


def parse_message(el):
    texts = []
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


def parse_time_views(el):
    date_el = el.find("time", datetime=True)
    if date_el:
        return date_el.get("datetime", "")
    return ""


def parse_views(el):
    vm = el.select_one(".tgme_widget_message_views")
    if vm:
        v = vm.get_text(strip=True).replace(",", "").replace(".", "")
        try:
            return int(v)
        except:
            pass
    reactions = el.select(".tgme_widget_message_reaction span")
    if reactions:
        total = 0
        for r in reactions:
            try:
                total += int(r.get_text(strip=True))
            except:
                pass
        return total
    return 0


def parse_page(html, channel):
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
        ]))

    return items


def assign_dates(items):
    now = datetime.now(ARABIC_TZ)
    current_date = now.date()
    last_hour = 99
    seen_hours = set()
    day_change_count = 0

    day_names = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
    month_names = [
        "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
    ]

    for item in items:
        t = item.get("time", "")
        if t:
            try:
                h = int(t[:2])
            except:
                h = 12
        else:
            h = 12

        if last_hour < 99 and h > 12 and last_hour < 6:
            day_change_count += 1
            current_date -= timedelta(days=1)
        elif last_hour < 99 and h < 6 and last_hour >= 12:
            pass  # same day, early morning
        elif last_hour < 99 and h > last_hour + 4:
            # big jump forward suggests new day
            current_date -= timedelta(days=1)

        last_hour = h

        d = current_date
        item["date"] = f"{day_names[d.weekday()]} {d.day} {month_names[d.month]} {d.year}"

    return items


def main():
    all_news = []
    seen = set()

    for ch in CHANNELS:
        print(f"Fetching @{ch}...")
        try:
            resp = requests.get(f"https://t.me/s/{ch}", headers=HEADERS, timeout=30)
            resp.raise_for_status()
            items = parse_page(resp.text, ch)
            for item in items:
                key = f"{ch}:{item['text'][:80]}"
                if key not in seen:
                    seen.add(key)
                    all_news.append(item)
            print(f"  Got {len(items)} items")
        except Exception as e:
            print(f"  Error: {e}")

    all_news = assign_dates(all_news)
    all_news = all_news[:MAX_ITEMS]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    print(f"Total: {len(all_news)} items saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
