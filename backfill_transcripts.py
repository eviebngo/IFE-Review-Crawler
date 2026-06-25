"""
Retroactively fetches transcripts for all YouTube videos in the cache
that currently have no transcript.

Strategy (in order):
  1. youtube-transcript-api (fast, free — manual + auto captions)
  2. OpenAI Whisper via yt-dlp audio download (covers videos with no captions)

Requires OPENAI_API_KEY in .env for the Whisper fallback.
Saves a checkpoint every 25 videos.
"""
import json
import os
import sys
import time
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from youtube_transcript_api import YouTubeTranscriptApi

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

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


def segs_to_result(segs, n=5):
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


def fetch_yt_segs(api, video_id):
    """Try YouTube transcript API (manual → auto-generated → any language)."""
    try:
        fetched = api.fetch(video_id, languages=[
            "en", "en-US", "en-GB",
            "fr", "de", "ja", "ko", "zh", "zh-TW", "zh-CN",
            "es", "pt", "tr", "it", "ar", "nl", "fi", "no",
        ])
        return [{"text": s.text, "start": s.start} for s in fetched]
    except Exception:
        pass
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


def fetch_whisper_segs(video_id):
    """Download audio with yt-dlp and transcribe with OpenAI Whisper."""
    if not OPENAI_KEY:
        return None
    try:
        import yt_dlp
        import openai
    except ImportError:
        return None

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "format": "worstaudio/worst",
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            files = os.listdir(tmpdir)
            if not files:
                return None
            audio_path = os.path.join(tmpdir, files[0])

            if os.path.getsize(audio_path) > 24 * 1024 * 1024:
                print(f"    audio too large ({os.path.getsize(audio_path)//1024//1024}MB), skipping Whisper")
                return None

            client = openai.OpenAI(api_key=OPENAI_KEY)
            with open(audio_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

        if not getattr(result, "segments", None):
            return None
        return [{"text": seg.text, "start": seg.start} for seg in result.segments]
    except Exception as e:
        print(f"    Whisper error: {e}")
        return None


def main():
    with open("ife_cache.json", encoding="utf-8") as f:
        data = json.load(f)

    reviews = data.get("reviews", [])
    targets = [
        r for r in reviews
        if "youtube.com/watch?v=" in r.get("url", "") and not r.get("transcript_available")
    ]
    print(f"Videos without transcript: {len(targets)}")
    if OPENAI_KEY:
        print("Whisper fallback: ENABLED")
    else:
        print("Whisper fallback: DISABLED (set OPENAI_API_KEY to enable)")

    api = YouTubeTranscriptApi()
    yt_ok = yt_fail = whisper_ok = whisper_fail = 0

    for idx, r in enumerate(targets, 1):
        vid_id = r["url"].split("watch?v=")[1].split("&")[0]

        # 1. YouTube transcript API
        segs = fetch_yt_segs(api, vid_id)
        if segs:
            caps, excerpt = segs_to_result(segs)
            r["transcript_available"] = True
            r["transcript_excerpt"] = excerpt
            r["captions"] = caps
            yt_ok += 1
            print(f"[{idx}/{len(targets)}] YT-OK    {vid_id}")
        else:
            # 2. Whisper fallback
            segs = fetch_whisper_segs(vid_id)
            if segs:
                caps, excerpt = segs_to_result(segs)
                r["transcript_available"] = True
                r["transcript_excerpt"] = excerpt
                r["captions"] = caps
                r["transcript_source"] = "whisper"
                whisper_ok += 1
                print(f"[{idx}/{len(targets)}] WH-OK    {vid_id}  ({len(caps)} caps via Whisper)")
            else:
                whisper_fail += 1
                yt_fail += 1
                print(f"[{idx}/{len(targets)}] FAIL     {vid_id}")

        if idx % 25 == 0:
            with open("ife_cache.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  -- checkpoint: YT={yt_ok} Whisper={whisper_ok} fail={whisper_fail} --")

        time.sleep(0.5)

    with open("ife_cache.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone.")
    print(f"  YouTube captions:  {yt_ok} ok")
    print(f"  Whisper:           {whisper_ok} ok")
    print(f"  Still missing:     {whisper_fail}")


if __name__ == "__main__":
    main()
