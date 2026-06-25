"""
Retroactively fetches transcripts for all YouTube videos in the cache
that currently have no transcript.

Strategy (in order):
  1. youtube-transcript-api  — fast, free, manual + auto captions
  2. Local Whisper via yt-dlp — covers videos with no YouTube captions at all

No API keys required. Requires: yt-dlp, openai-whisper, ffmpeg in PATH.
Set WHISPER_MODEL env var to override model size (default: base).
Saves a checkpoint every 25 videos.
"""
import json
import os
import sys
import time
import tempfile
from pathlib import Path

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


def load_whisper_model():
    """Load local Whisper model once. Returns None if not installed."""
    try:
        import whisper
        size = os.environ.get("WHISPER_MODEL", "base")
        print(f"Loading Whisper '{size}' model (first run downloads ~145MB)...")
        return whisper.load_model(size)
    except ImportError:
        print("openai-whisper not installed — run: pip install openai-whisper")
        return None
    except Exception as e:
        print(f"Whisper load error: {e}")
        return None


def fetch_whisper_segs(model, video_id):
    """Download audio with yt-dlp and transcribe with local Whisper."""
    if model is None:
        return None
    try:
        import yt_dlp
    except ImportError:
        print("  yt-dlp not installed — run: pip install yt-dlp")
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
            result = model.transcribe(audio_path, verbose=False)

        segments = result.get("segments") or []
        if not segments:
            return None
        return [{"text": seg["text"], "start": seg["start"]} for seg in segments]
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

    api = YouTubeTranscriptApi()
    whisper_model = load_whisper_model()
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
            # 2. Local Whisper fallback
            segs = fetch_whisper_segs(whisper_model, vid_id)
            if segs:
                caps, excerpt = segs_to_result(segs)
                r["transcript_available"] = True
                r["transcript_excerpt"] = excerpt
                r["captions"] = caps
                r["transcript_source"] = "whisper"
                whisper_ok += 1
                print(f"[{idx}/{len(targets)}] WH-OK    {vid_id}  ({len(caps)} caps)")
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
