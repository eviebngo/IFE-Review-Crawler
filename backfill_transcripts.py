"""
Retroactively fetches real transcripts for all YouTube videos in the cache
that currently have no transcript. Tries manual captions first, then
auto-generated. Updates ife_cache.json in place.
"""
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

from youtube_transcript_api import YouTubeTranscriptApi

IFE_KEYWORDS = [
    "ife", "inflight entertainment", "in-flight entertainment",
    "screen", "display", "touchscreen", "monitor",
    "movie", "movies", "tv show", "content", "channels",
    "wifi", "wi-fi", "internet", "bluetooth",
    "panasonic", "thales", "safran", "rave", "emirates ice", "krisworld", "oryx",
    "entertainment system", "seatback", "headphone", "usb", "charging",
    "resolution", "4k", "1080p", "hd", "audio", "video on demand", "vod",
    "seat", "cabin", "business class", "economy", "first class",
    "entertainment", "airline", "flight",
]


def score_seg(text):
    t = text.lower()
    return sum(1 for kw in IFE_KEYWORDS if kw in t)


def pick_caps(segs, n=5):
    scored = sorted(enumerate(segs), key=lambda x: -score_seg(x[1]["text"]))
    chosen = []
    for i, seg in scored:
        if all(abs(i - j) >= 10 for j in chosen):
            chosen.append(i)
        if len(chosen) >= n:
            break
    if len(chosen) < n:
        step = max(1, len(segs) // n)
        for k in range(0, len(segs), step):
            if all(abs(k - j) >= 5 for j in chosen) and len(chosen) < n:
                chosen.append(k)
    chosen.sort()
    caps = []
    for i in chosen[:n]:
        s = segs[i]
        raw = int(s["start"])
        m, sec = raw // 60, raw % 60
        caps.append({"timestamp": f"{m}:{sec:02d}", "start_seconds": raw, "text": s["text"].strip()})
    best_idx = scored[0][0] if scored else 0
    excerpt = segs[best_idx]["text"].strip() if segs else ""
    return caps, excerpt


def fetch_segs(api, video_id):
    try:
        fetched = api.fetch(video_id, languages=[
            "en", "en-US", "en-GB",
            "fr", "de", "ja", "ko", "zh", "zh-TW", "zh-CN",
            "es", "pt", "tr", "it", "ar", "nl", "fi", "no",
        ])
        return [{"text": s.text, "start": s.start} for s in fetched]
    except Exception:
        pass
    # Fall back: try every available transcript (any language, manual or auto-generated)
    try:
        tlist = api.list(video_id)
        for t in sorted(tlist, key=lambda x: x.is_generated):
            try:
                segs = [{"text": s.text, "start": s.start} for s in t.fetch()]
                if segs:
                    return segs
            except Exception:
                continue
    except Exception:
        pass
    return None


def main():
    with open("ife_cache.json", encoding="utf-8") as f:
        data = json.load(f)

    reviews = data.get("reviews", [])
    targets = [
        r for r in reviews
        if "youtube.com/watch?v=" in r.get("url", "") and not r.get("transcript_available")
    ]
    print(f"Videos to process: {len(targets)}")

    api = YouTubeTranscriptApi()
    patched = 0
    failed = 0

    for idx, r in enumerate(targets, 1):
        vid_id = r["url"].split("watch?v=")[1].split("&")[0]
        segs = fetch_segs(api, vid_id)
        if segs:
            caps, excerpt = pick_caps(segs)
            r["transcript_available"] = True
            r["transcript_excerpt"] = excerpt
            r["captions"] = caps
            patched += 1
            print(f"[{idx}/{len(targets)}] OK   {vid_id} ({len(caps)} caps)")
        else:
            failed += 1
            print(f"[{idx}/{len(targets)}] FAIL {vid_id}")
        # Save every 25 videos in case of interruption
        if idx % 25 == 0:
            with open("ife_cache.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  -- checkpoint saved ({patched} patched, {failed} failed so far) --")
        time.sleep(0.3)

    with open("ife_cache.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Patched: {patched} | Failed: {failed} | Total: {len(targets)}")


if __name__ == "__main__":
    main()
