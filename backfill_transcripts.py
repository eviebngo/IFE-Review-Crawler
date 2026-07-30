"""
Retroactively fetches transcripts for all YouTube videos in the cache
that currently have no transcript.

Strategy (in order):
  1. youtube-transcript-api  — fast, free, manual + auto captions
  2. Local Whisper via yt-dlp — covers videos with no YouTube captions at all

Env vars:
  YOUTUBE_COOKIES_B64  — base64-encoded Netscape cookies.txt (bypasses IP block)
  WHISPER_MODEL        — Whisper model size (default: base)
"""
import base64
import json
import os
import sys
import time
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from youtube_transcript_api import YouTubeTranscriptApi

# Write cookies.txt from env if provided, return path or None
def _setup_cookies(tmpdir: str) -> str | None:
    b64 = os.environ.get("YOUTUBE_COOKIES_B64", "").strip()
    if not b64:
        return None
    try:
        path = os.path.join(tmpdir, "cookies.txt")
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return path
    except Exception as e:
        print(f"  Warning: could not decode YOUTUBE_COOKIES_B64 — {e}")
        return None

from ife_crawler import IFECrawler, IFE_FEATURE_KEYWORDS, IFE_SYSTEM_PATTERNS

# Reuse the crawler's strict IFE caption picker (drops greetings/filler, no
# evenly-spaced padding) so Whisper captions match the rest of the app.
_SCORE_KWS = (
    [kw for kws in IFE_FEATURE_KEYWORDS.values() for kw in kws]
    + [p for ps in IFE_SYSTEM_PATTERNS.values() for p in ps]
)


def segs_to_result(segs):
    excerpt, caps, full = IFECrawler._segs_to_caps(segs, _SCORE_KWS)
    return caps, excerpt, full


def fetch_yt_segs(video_id, cookies_path=None):
    """Try YouTube transcript API (manual → auto-generated → any language)."""
    try:
        api = YouTubeTranscriptApi(cookies=cookies_path) if cookies_path else YouTubeTranscriptApi()
    except TypeError:
        api = YouTubeTranscriptApi()
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


# Broadened from a single incident — yt-dlp/YouTube phrase bot-detection and
# rate-limiting differently depending on which wall you hit.
_BOT_SIGNALS = (
    "sign in to confirm", "not a bot", "sign in if you", "unusual traffic",
    "confirm you're not a bot", "confirm that you are not a bot",
    "429", "too many requests", "rate limit", "http error 403", "forbidden",
)
_SKIP_SIGNALS = ("private video", "video unavailable", "has been removed", "account has been terminated")

# Return values for fetch_whisper_segs
_WHISPER_OK    = "ok"
_WHISPER_SKIP  = "skip"   # private/unavailable — remove from cache
_WHISPER_BLOCK = "block"  # bot-detected — stop trying Whisper for this run
_WHISPER_FAIL  = "fail"   # generic failure


class _SilentLogger:
    """Captures yt-dlp error text without printing it."""
    def __init__(self):
        self.errors = []
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): self.errors.append(msg.lower())


def _browser_cookie_opts():
    """Try to borrow a real logged-in YouTube session from a local browser —
    far less likely to look like a bot than an anonymous request. Silently
    unavailable on CI runners / machines with no matching browser profile."""
    for browser in ("edge", "chrome", "firefox"):
        try:
            import yt_dlp
            # Cheap probe: let yt-dlp's own cookie extractor try to open the
            # profile. If it can't find/decrypt one, this raises.
            from yt_dlp.cookies import extract_cookies_from_browser
            extract_cookies_from_browser(browser)
            return {"cookiesfrombrowser": (browser,)}
        except Exception:
            continue
    return {}


def fetch_whisper_segs(model, video_id, cookies_path=None, browser_cookie_opts=None):
    """Download audio with yt-dlp and transcribe with local Whisper.
    Returns (status, segs, detail) where status is one of the _WHISPER_*
    constants and detail is a short human-readable reason (for FAIL/BLOCK)."""
    if model is None:
        return _WHISPER_FAIL, None, "whisper model not loaded"
    try:
        import yt_dlp
    except ImportError:
        return _WHISPER_FAIL, None, "yt-dlp not installed"

    logger = _SilentLogger()
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "format": "worstaudio/worst",
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "nocheckcertificate": True,
                "logger": logger,
            }
            if cookies_path:
                ydl_opts["cookiefile"] = cookies_path
            elif browser_cookie_opts:
                ydl_opts.update(browser_cookie_opts)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Check captured errors even if download didn't raise
            combined = " ".join(logger.errors)
            if any(s in combined for s in _SKIP_SIGNALS):
                return _WHISPER_SKIP, None, combined[:200]
            if any(s in combined for s in _BOT_SIGNALS):
                return _WHISPER_BLOCK, None, combined[:200]

            files = os.listdir(tmpdir)
            if not files:
                return _WHISPER_FAIL, None, ("yt-dlp produced no file; " + combined[:150]) if combined else "yt-dlp produced no output file"
            audio_path = os.path.join(tmpdir, files[0])
            file_size = os.path.getsize(audio_path)
            result = model.transcribe(audio_path, verbose=False)

        segments = result.get("segments") or []
        if not segments:
            # A suspiciously tiny download (a few KB) alongside zero speech is a
            # much more likely sign of a blocked/placeholder stream than of a
            # genuinely silent multi-minute review video.
            if file_size < 30_000:
                return _WHISPER_BLOCK, None, f"no speech detected + tiny audio file ({file_size}B) — likely blocked/placeholder stream"
            return _WHISPER_FAIL, None, "no speech detected in audio"
        return _WHISPER_OK, [{"text": seg["text"], "start": seg["start"]} for seg in segments], None

    except Exception as e:
        msg = str(e).lower()
        if any(s in msg for s in _SKIP_SIGNALS):
            return _WHISPER_SKIP, None, str(e)[:200]
        if any(s in msg for s in _BOT_SIGNALS):
            return _WHISPER_BLOCK, None, str(e)[:200]
        return _WHISPER_FAIL, None, str(e)[:200]


def main():
    with open("ife_cache.json", encoding="utf-8") as f:
        data = json.load(f)

    reviews = data.get("reviews", [])
    targets = [
        r for r in reviews
        if "youtube.com/watch?v=" in r.get("url", "") and not r.get("transcript_available")
    ]
    print(f"Videos without transcript: {len(targets)}")

    # Set up cookies (bypasses IP block on GitHub Actions datacenter IPs)
    _cookie_dir = tempfile.mkdtemp()
    cookies_path = _setup_cookies(_cookie_dir)
    browser_cookie_opts = {}
    if cookies_path:
        print("  Using YOUTUBE_COOKIES_B64 for authentication.")
    else:
        browser_cookie_opts = _browser_cookie_opts()
        if browser_cookie_opts:
            print(f"  Using local browser cookies ({browser_cookie_opts['cookiesfrombrowser'][0]}) for authentication.")
        else:
            print("  No cookies available (no YOUTUBE_COOKIES_B64, no usable local browser profile) — some videos may be IP-blocked.")

    whisper_model = load_whisper_model()
    yt_ok = whisper_ok = skipped = blocked = failed = 0
    to_remove = []   # private / unavailable video URLs
    whisper_blocked = False

    for idx, r in enumerate(targets, 1):
        vid_id = r["url"].split("watch?v=")[1].split("&")[0]

        # 1. YouTube transcript API
        segs = fetch_yt_segs(vid_id, cookies_path=cookies_path)
        if segs:
            caps, excerpt, full = segs_to_result(segs)
            r["transcript_available"] = True
            r["transcript_excerpt"] = excerpt
            r["captions"] = caps
            r["transcript_full"] = full
            yt_ok += 1
            print(f"[{idx}/{len(targets)}] YT-OK    {vid_id}")

        elif whisper_blocked:
            failed += 1
            print(f"[{idx}/{len(targets)}] SKIP-WH  {vid_id}  (bot-blocked on this runner)")

        else:
            # 2. Local Whisper fallback
            status, segs, detail = fetch_whisper_segs(
                whisper_model, vid_id, cookies_path=cookies_path, browser_cookie_opts=browser_cookie_opts
            )
            if status == _WHISPER_OK:
                caps, excerpt, full = segs_to_result(segs)
                r["transcript_available"] = True
                r["transcript_excerpt"] = excerpt
                r["captions"] = caps
                r["transcript_full"] = full
                r["transcript_source"] = "whisper"
                whisper_ok += 1
                print(f"[{idx}/{len(targets)}] WH-OK    {vid_id}  ({len(caps)} caps)")
            elif status == _WHISPER_SKIP:
                to_remove.append(r["url"])
                skipped += 1
                print(f"[{idx}/{len(targets)}] REMOVED  {vid_id}  (private/unavailable)")
            elif status == _WHISPER_BLOCK:
                whisper_blocked = True
                failed += 1
                print(f"[{idx}/{len(targets)}] BOT-BLOCK {vid_id}  ({detail or 'Whisper disabled for this run'})")
            else:
                failed += 1
                print(f"[{idx}/{len(targets)}] FAIL     {vid_id}  ({detail or 'unknown reason'})")

        if idx % 25 == 0:
            with open("ife_cache.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  -- checkpoint: YT={yt_ok} Whisper={whisper_ok} removed={skipped} fail={failed} --")

        time.sleep(0.5)

    # Purge private/unavailable videos from the cache
    if to_remove:
        before = len(data["reviews"])
        data["reviews"] = [r for r in data["reviews"] if r.get("url") not in set(to_remove)]
        print(f"\nPurged {before - len(data['reviews'])} private/unavailable videos.")

    with open("ife_cache.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone.")
    print(f"  YouTube captions:  {yt_ok}")
    print(f"  Whisper:           {whisper_ok}")
    print(f"  Purged (private):  {skipped}")
    print(f"  Still missing:     {failed}")
    if whisper_blocked:
        print("  NOTE: Whisper was bot-blocked — re-run locally with browser cookies for remaining videos.")


if __name__ == "__main__":
    main()
