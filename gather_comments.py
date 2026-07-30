"""
Gather real YouTube comments for cached videos via the Data API
(commentThreads.list — not IP-blocked). Keeps IFE-relevant comments and tags
each as either the channel's own comment (author == the video's channel) or a
viewer comment.

Stores on each review:
  yt_comments = [{"author","text","likes","when","is_channel"}]

Quota: commentThreads.list costs 1 unit/call. One call per video (top ~20
relevance-ranked threads) → ~1000 units, well under the 10k/day default.

Run:  python gather_comments.py     (needs YOUTUBE_API_KEY)
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

VIDEOS_API = "https://www.googleapis.com/youtube/v3/videos"
THREADS_API = "https://www.googleapis.com/youtube/v3/commentThreads"
KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
CACHE = Path(__file__).parent / "ife_cache.json"

# Reuse the same strong IFE vocabulary the comments feed already filters on so the
# stored comments stay on-topic (screens, seatback, wifi, system names, specs…).
# Comment relevance is STRICTER than the transcript filter: reviewers stay on
# topic, but random viewer comments do not. We use two tiers.
#
# STRONG: unambiguously about the IFE system → keep on a single match.
_STRONG_TERMS = (
    "inflight entertainment", "in-flight entertainment", "in flight entertainment",
    "entertainment system", "entertainment screen", "entertainment selection",
    "entertainment option", "seatback screen", "seat back screen", "seatback tv",
    "touchscreen", "touch screen", "seat back tv", "in-seat screen", "in seat screen",
    "avod", "moving map", "flight map", "live tv", "movie selection",
    "content selection", "film selection", "the ife", "ife system", "ife screen",
    "ife is", "ife was", "ife had", "screen was", "screen is", "screen quality",
    "4k screen", "oled screen", "hd screen", "the entertainment", "seatback",
    "seat-back", "panasonic", "thales", "avant up", "rave ", "safran",
    "panasonic ex", "moving-map", "ife", "ice ife", "ice system",
    # IFE system / product names
    "astrova", "avant", "krisworld", "oryx", "studiocx", "lumexis", "collins venue",
    "bluebox", "immfly", "anuvu", "viasat", "starlink", "inflyt",
    # IFE-system attributes praised in reviews/comments
    "mood lighting", "ambient lighting", "frame rate", "seatback display",
    "video on demand", "watch party", "seat-to-seat", "inflight connectivity",
    "in-flight connectivity", "4k oled", "mini-led", "mini led", "oled screen",
    "oled display", "usb-c port", "bluetooth headphone",
)
# WEAK: hardware terms that are IFE ONLY with supporting context (below).
# Deliberately NO generic content words (movie/movies/content/audio): "watching
# the movie X" is about a film, not the IFE system. IFE content is captured by
# the STRONG phrases ("movie selection", "content selection", "film selection").
_WEAK_TERMS = (
    "headphone", "headphones", "headset", "earphone", "earphones", "the screen",
    "screens", "display", "monitor", "usb", "usb-c", "power outlet", "power port",
    "charging port", "3.5mm", "wi-fi", "wifi", "bluetooth", "handset",
    "remote control", "oled", "4k",
)
# A WEAK term only counts as IFE when the comment also carries one of these.
# These must be IFE-specific — dropped bare "watch/flight/seat/airline" which
# let off-topic hardware chatter through.
_CONTEXT_TERMS = (
    "screen", "entertainment", "ife", "in-flight", "inflight", "seatback",
    "seat back", "plug in", "plug it", "headphone jack", "pair with", "3.5mm",
    "on the plane", "on the flight", "in my seat", "at my seat", "usb",
    "the system", "this system", "new system", "seatback", "in-seat", "avod",
)
# Comments that mention hardware but are clearly OFF-topic (jokes about keeping
# freebies, etc.) — reject even if a term matched.
_DISQUALIFY = (
    "take home", "take it home", "taking home", "free to take", "keep the",
    "keep it", "keep them", "get to keep", "steal", "stole", "pocket",
    "bring home", "give away", "giveaway", "for free", "souvenir",
    # seat fixtures / hardware that isn't the IFE system
    "headphone hook", "headphone holder", "coat hook", "cup holder", "bag hook",
)


def _re_any(terms):
    # Leading AND trailing word boundaries so a term must be a whole token:
    # "screen" must not match inside "screenshot", "usb" not in "usbc", etc.
    return re.compile(
        r"(?<![a-z0-9])(?:" + "|".join(re.escape(t) for t in terms) + r")(?![a-z0-9])",
        re.I)


_STRONG_RE = _re_any(_STRONG_TERMS)
_WEAK_RE = _re_any(_WEAK_TERMS)
_CTX_RE = _re_any(_CONTEXT_TERMS)
_DQ_RE = re.compile("|".join(re.escape(t) for t in _DISQUALIFY), re.I)

_HTML_TAG = re.compile(r"<[^>]+>")


def _clean(text):
    """Strip the HTML YouTube returns in comment bodies, unescape a few entities."""
    text = _HTML_TAG.sub(" ", text or "")
    text = (text.replace("&quot;", '"').replace("&#39;", "'")
                .replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<"))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_ife(text):
    """Strict two-tier test. Strong term → keep. Weak term → keep only with
    supporting context. Off-topic 'take it home' jokes → always reject."""
    if _DQ_RE.search(text):
        return False
    if _STRONG_RE.search(text):
        return True
    if _WEAK_RE.search(text) and _CTX_RE.search(text):
        return True
    return False


def video_channel_ids(ids):
    """Map video_id -> channel_id (to flag the uploader's own comments)."""
    out = {}
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        try:
            resp = requests.get(VIDEOS_API, params={
                "part": "snippet", "id": ",".join(batch), "key": KEY},
                timeout=20, verify=False)
            if resp.status_code != 200:
                continue
            for item in resp.json().get("items", []):
                out[item["id"]] = item.get("snippet", {}).get("channelId")
        except Exception as e:
            print(f"  channel-id batch failed: {e}")
    return out


def fetch_comments(video_id, uploader_channel_id, max_keep=8):
    """Return up to max_keep IFE-relevant comment dicts for a video."""
    try:
        resp = requests.get(THREADS_API, params={
            "part": "snippet", "videoId": video_id, "maxResults": 50,
            "order": "relevance", "textFormat": "plainText", "key": KEY},
            timeout=20, verify=False)
    except Exception:
        return None, "request-error"
    if resp.status_code == 403:
        # comments disabled, or quota — distinguish by reason
        reason = ""
        try:
            reason = resp.json().get("error", {}).get("errors", [{}])[0].get("reason", "")
        except Exception:
            pass
        return [], reason or "forbidden"
    if resp.status_code == 404:
        return [], "not-found"
    if resp.status_code != 200:
        return None, f"http-{resp.status_code}"

    kept = []
    for th in resp.json().get("items", []):
        top = th.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        text = _clean(top.get("textDisplay") or top.get("textOriginal"))
        if len(text) < 20 or not _is_ife(text):
            continue
        author_ch = (top.get("authorChannelId") or {}).get("value")
        kept.append({
            "author": top.get("authorDisplayName") or "Viewer",
            "text": text,
            "likes": int(top.get("likeCount") or 0),
            "when": top.get("publishedAt", "")[:10],
            "is_channel": bool(uploader_channel_id and author_ch == uploader_channel_id),
        })
        if len(kept) >= max_keep:
            break
    # channel's own comments first, then most-liked
    kept.sort(key=lambda c: (not c["is_channel"], -c["likes"]))
    return kept, None


def main():
    if not KEY:
        print("ERROR: YOUTUBE_API_KEY not set.")
        sys.exit(1)
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    reviews = data.get("reviews", [])
    by_id = {}
    for r in reviews:
        u = r.get("url", "")
        if "youtube.com/watch?v=" in u:
            by_id.setdefault(u.split("watch?v=")[1].split("&")[0], []).append(r)
    ids = list(by_id)
    print(f"Fetching comments for {len(ids)} videos…")

    print("  Resolving uploader channel IDs…")
    ch_map = video_channel_ids(ids)

    with_comments = total_kept = disabled = errors = 0
    for i, vid in enumerate(ids, 1):
        comments, err = fetch_comments(vid, ch_map.get(vid))
        if comments is None:
            errors += 1
            if err and ("quota" in err.lower() or err == "http-403"):
                print(f"  [{i}] quota/blocked ({err}) — stopping early, saving progress.")
                break
            continue
        if err in ("commentsDisabled", "not-found"):
            disabled += 1
        for r in by_id.get(vid, []):
            r["yt_comments"] = comments
        if comments:
            with_comments += 1
            total_kept += len(comments)
        if i % 50 == 0:
            CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  [{i}/{len(ids)}] videos-with-IFE-comments={with_comments} "
                  f"kept={total_kept} disabled={disabled} err={errors}")
        time.sleep(0.02)

    CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. {with_comments} videos have IFE comments ({total_kept} total). "
          f"comments-disabled/none={disabled}, errors={errors}. Saved {CACHE.name}.")


if __name__ == "__main__":
    main()
