"""
Gather follower counts for the known independent IFE reviewer channels and
backfill per-video like counts into the review cache.

Writes:
  channel_stats.json   — {name: {channel_id, title, subscribers, video_count, thumb}}
  ife_cache.json       — adds `like_count` (and refreshes `view_count`) on YouTube videos

Run:  python gather_channel_stats.py
Needs YOUTUBE_API_KEY (from .env).
"""
import json
import os
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from ife_crawler import KNOWN_IFE_CHANNELS

API = "https://www.googleapis.com/youtube/v3"
KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
CACHE = Path(__file__).parent / "ife_cache.json"
STATS = Path(__file__).parent / "channel_stats.json"


def _independent():
    return {n: c for n, c in KNOWN_IFE_CHANNELS.items() if "(official)" not in n.lower()}


def fetch_channel_stats():
    chans = _independent()
    ids = list(chans.values())
    resp = requests.get(f"{API}/channels",
                        params={"part": "snippet,statistics", "id": ",".join(ids), "key": KEY},
                        timeout=20)
    resp.raise_for_status()
    by_id = {it["id"]: it for it in resp.json().get("items", [])}
    out = {}
    for name, cid in chans.items():
        it = by_id.get(cid)
        if not it:
            continue
        sn, st = it.get("snippet", {}), it.get("statistics", {})
        thumbs = sn.get("thumbnails", {})
        out[name] = {
            "channel_id": cid,
            "title": sn.get("title", name),
            "subscribers": int(st.get("subscriberCount", 0) or 0),
            "video_count": int(st.get("videoCount", 0) or 0),
            "thumb": (thumbs.get("default") or {}).get("url", ""),
        }
    return out


def backfill_like_counts(data):
    reviews = data.get("reviews", [])
    vids = {}
    for r in reviews:
        u = r.get("url", "")
        if "youtube.com/watch?v=" in u:
            vids.setdefault(u.split("watch?v=")[1].split("&")[0], []).append(r)
    ids = list(vids)
    updated = 0
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        resp = requests.get(f"{API}/videos",
                            params={"part": "statistics", "id": ",".join(batch), "key": KEY},
                            timeout=20)
        if resp.status_code != 200:
            print(f"  videos.list batch failed: {resp.status_code}")
            continue
        for it in resp.json().get("items", []):
            st = it.get("statistics", {})
            for r in vids.get(it["id"], []):
                r["like_count"] = int(st.get("likeCount", 0) or 0)
                r["view_count"] = int(st.get("viewCount", r.get("view_count", 0)) or 0)
                updated += 1
    return updated


def main():
    if not KEY:
        print("ERROR: YOUTUBE_API_KEY not set.")
        sys.exit(1)

    print(f"Fetching stats for {len(_independent())} independent channels…")
    stats = fetch_channel_stats()
    STATS.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {STATS.name} ({len(stats)} channels)")
    for name, s in sorted(stats.items(), key=lambda x: -x[1]["subscribers"]):
        print(f"    {name:<24} {s['subscribers']:>10,} subs   {s['video_count']:>4} videos")

    print("\nBackfilling per-video like counts into the cache…")
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    n = backfill_like_counts(data)
    CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  updated like_count/view_count on {n} videos; saved {CACHE.name}")


if __name__ == "__main__":
    main()
