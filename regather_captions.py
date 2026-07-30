"""
Re-fetch transcripts and REGENERATE captions for cached videos using the strict
IFE caption picker — including videos that were transcribed earlier with the old
(weak) picker. Prefers the fast YouTube caption API (cookies unblock it), falling
back to local Whisper only when a video has no captions.

Targets any YouTube video missing a transcript OR missing the stored full
transcript (i.e. everything picked before transcript_full existed).

Cookies (to bypass the datacenter/IP block), in priority order:
  1. cookies.txt in this folder (Netscape format, exported from a logged-in browser)
  2. YOUTUBE_COOKIES_B64 env var (base64 of cookies.txt)
  3. a local logged-in browser profile (edge/chrome/firefox)

Run:  python regather_captions.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import backfill_transcripts as bt  # reuse fetch_yt_segs / whisper / strict segs_to_result

CACHE = Path(__file__).parent / "ife_cache.json"


def main():
    no_whisper = "--no-whisper" in sys.argv
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    reviews = data.get("reviews", [])
    targets = [r for r in reviews
               if "youtube.com/watch?v=" in r.get("url", "")
               and (not r.get("transcript_available") or not r.get("transcript_full"))]
    print(f"Videos to (re)gather captions for: {len(targets)}"
          + ("  (captions-only, Whisper disabled)" if no_whisper else ""))

    # resolve cookies
    tmp = tempfile.mkdtemp()
    cj = Path(__file__).parent / "cookies.txt"
    cookies_path = str(cj) if cj.exists() else bt._setup_cookies(tmp)
    browser_opts = {}
    if cookies_path:
        print(f"  Using cookies: {cookies_path if cj.exists() else 'YOUTUBE_COOKIES_B64'}")
    else:
        browser_opts = bt._browser_cookie_opts()
        print("  " + (f"Using browser cookies ({browser_opts['cookiesfrombrowser'][0]})."
                      if browser_opts else "No cookies — the caption API is likely IP-blocked; Whisper may bot-block."))

    whisper_model = None
    yt_ok = wh_ok = skipped = failed = 0
    whisper_blocked = False
    to_remove = []

    for idx, r in enumerate(targets, 1):
        vid = r["url"].split("watch?v=")[1].split("&")[0]
        segs = bt.fetch_yt_segs(vid, cookies_path=cookies_path)
        if segs:
            caps, excerpt, full = bt.segs_to_result(segs)
            r.update({"transcript_available": True, "transcript_excerpt": excerpt,
                      "captions": caps, "transcript_full": full})
            yt_ok += 1
            print(f"[{idx}/{len(targets)}] YT-OK    {vid}  ({len(caps)} caps)")
        elif no_whisper or whisper_blocked:
            failed += 1
        else:
            if whisper_model is None:
                whisper_model = bt.load_whisper_model()
            status, wsegs, detail = bt.fetch_whisper_segs(
                whisper_model, vid, cookies_path=cookies_path, browser_cookie_opts=browser_opts)
            if status == bt._WHISPER_OK:
                caps, excerpt, full = bt.segs_to_result(wsegs)
                r.update({"transcript_available": True, "transcript_excerpt": excerpt,
                          "captions": caps, "transcript_full": full, "transcript_source": "whisper"})
                wh_ok += 1
                print(f"[{idx}/{len(targets)}] WH-OK    {vid}  ({len(caps)} caps)")
            elif status == bt._WHISPER_SKIP:
                to_remove.append(r["url"]); skipped += 1
                print(f"[{idx}/{len(targets)}] REMOVED  {vid}  (private/unavailable)")
            elif status == bt._WHISPER_BLOCK:
                whisper_blocked = True; failed += 1
                print(f"[{idx}/{len(targets)}] BOT-BLOCK {vid}  ({detail or ''})")
            else:
                failed += 1

        if idx % 25 == 0:
            CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  -- checkpoint: YT={yt_ok} Whisper={wh_ok} removed={skipped} fail={failed} --")

    if to_remove:
        data["reviews"] = [r for r in reviews if r.get("url") not in set(to_remove)]
    CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. YouTube={yt_ok}  Whisper={wh_ok}  removed={skipped}  still-missing={failed}")
    if whisper_blocked:
        print("  NOTE: Whisper bot-blocked — provide cookies.txt for reliable results.")


if __name__ == "__main__":
    main()
