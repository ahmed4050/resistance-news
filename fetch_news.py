#!/usr/bin/env python3
"""Fetch news from Telegram channels and save as news.json"""

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from html import unescape
from collections import OrderedDict

import requests

CHANNELS = [
    "hezbulla",
    "PalestineResist",
    "manarnews1",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
ARABIC_TZ = timezone(timedelta(hours=3))

OUTPUT_FILE = "news.json"
MAX_ITEMS = 200


def clean_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = unescape(text)
    return text


def parse_telegram_page(html, channel):
    items = []

    # Split into post blocks
    blocks = re.split(r'<div class="tgme_widget_message_wrap[^"]*"[^>]*>', html)

    for block in blocks:
        if not block.strip():
            continue

        text = ""
        views = 0
        time_str = ""
        date_str = ""
        reactions = {}

        post = block

        # Extract text
        text_matches = re.findall(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*</div>',
            post,
            re.DOTALL,
        )
        if text_matches:
            raw = text_matches[0]
            raw = re.sub(r"<[^>]+>", " ", raw)
            text = clean_text(raw)
        else:
            # Fallback: look for #hashtags and bold text
            fallback = re.sub(r"<[^>]+>", " ", post)
            fallback = clean_text(fallback)
            if len(fallback) > 20:
                text = fallback

        if not text or len(text) < 5:
            continue

        # Skip forwarded-from banners
        if text.startswith("Forwarded from") and len(text) < 40:
            continue

        # Extract views
        vm = re.search(r'class="tgme_widget_message_views[^"]*"[^>]*>([^<]+)', post)
        if vm:
            try:
                views = int(vm.group(1).replace(",", "").replace("K", "000"))
            except:
                views = 0

        # Extract time (HH:MM)
        tm = re.search(r'class="tgme_widget_message_date[^"]*"[^>]*>([^<]+)', post)
        if tm:
            raw_time = clean_text(tm.group(1))
            tm2 = re.search(r"(\d{2}:\d{2})", raw_time)
            if tm2:
                time_str = tm2.group(1)

        # Extract reactions
        rms = re.findall(
            r'class="tgme_widget_message_reaction[^"]*"[^>]*>.*?<span[^>]*>(\d+)</span>',
            post,
        )
        if rms:
            total = sum(int(r) for r in rms)
            views = max(views, total)

        # Determine date based on time
        # If time is between 00:00-05:59, it's likely current day (early morning)
        # Otherwise, assume previous day for older posts
        if time_str:
            try:
                h, m = time_str.split(":")
                h = int(h)
                now = datetime.now(ARABIC_TZ)
                post_dt = now.replace(hour=h, minute=int(m), second=0, microsecond=0)
                if post_dt > now:
                    post_dt -= timedelta(days=1)
                # Group by date
                if h < 6:
                    date_str = post_dt.strftime("%A %d %B %Y")
                # For the page, we'll use relative dates
            except:
                pass

        items.append(
            OrderedDict(
                [
                    ("channel", channel),
                    ("text", text[:1500]),
                    ("time", time_str),
                    ("views", views),
                    ("reactions", reactions),
                ]
            )
        )

    return items


def fetch_channel(channel):
    url = f"https://t.me/s/{channel}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return parse_telegram_page(resp.text, channel)
    except Exception as e:
        print(f"  Error fetching {channel}: {e}")
        return []


def assign_dates(items):
    """Assign dates to items based on position and time"""
    now = datetime.now(ARABIC_TZ)
    today = now.date()

    # We'll work backwards: most recent items (first in list) are newest
    current_date = today
    last_time_hour = 99
    items_with_dates = []

    for item in items:
        t = item.get("time", "")
        if t:
            try:
                h = int(t.split(":")[0])
            except:
                h = 12
        else:
            h = 12

        # If time jumps from low (early AM) to high, or we see a time reset,
        # it might be a new day. But since Telegram shows newest first,
        # items are in reverse chronological order within the same day.
        # We can't perfectly detect day boundaries without dates.
        # Use a simple heuristic: if the time is much earlier, it's likely
        # an earlier day.
        if h > last_time_hour and last_time_hour < 99:
            current_date -= timedelta(days=1)
        last_time_hour = h

        # Arabic day names
        day_names = {
            0: "الإثنين", 1: "الثلاثاء", 2: "الأربعاء",
            3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد",
        }
        month_names = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
            5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
            9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
        }
        item["date"] = f"{day_names[current_date.weekday()]} {current_date.day} {month_names[current_date.month]} {current_date.year}"
        items_with_dates.append(item)

    return items_with_dates


def main():
    all_news = []
    seen = set()

    for ch in CHANNELS:
        print(f"Fetching @{ch}...")
        try:
            items = fetch_channel(ch)
            for item in items:
                # Deduplicate
                key = f"{ch}:{item['text'][:100]}"
                if key not in seen:
                    seen.add(key)
                    all_news.append(item)
            print(f"  Got {len(items)} items")
        except Exception as e:
            print(f"  Failed: {e}")

    # Sort: newest first (Telegram returns newest first)
    all_news = assign_dates(all_news)

    # Keep max items
    all_news = all_news[:MAX_ITEMS]

    # Write JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    print(f"Total: {len(all_news)} items saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
