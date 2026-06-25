import re
import json
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    TRANSCRIPTS_AVAILABLE = True
except ImportError:
    TRANSCRIPTS_AVAILABLE = False


# ── Source reputation tiers ───────────────────────────────────────────────────
# Tier 1: established aviation / travel trade press
# Tier 2: known aviation YouTube channels / specialist blogs
# Tier 3: general / unknown

SOURCE_TIERS = {
    # Tier 1 — aviation & travel trade press
    1: [
        "simpleflying.com", "airlinegeeks.com", "aviationweek.com",
        "thepointsguy.com", "onemileatatime.com", "boardingarea.com",
        "airlinereporter.com", "skift.com", "flightglobal.com",
        "routesonline.com", "ch-aviation.com", "atwonline.com",
        "aerotime.aero", "aviationbusinessnews.com", "passengerexperience.aero",
        "apex.aero", "aircraft-interior-expo.com",
        "paxinternational.com", "businesstraveller.com", "airlineratings.com",
        "ainonline.com", "aircraft-interiors-international.com", "runwaygirlnetwork.com",
        "aviationpros.com", "cntraveler.com", "travelandleisure.com",
    ],
    # Tier 2 — specialist aviation/travel creators and blogs
    2: [
        "youtube.com", "samchui.com", "noelphilips.com",
        "flyertalk.com", "airfarewatchdog.com", "headsforaplane.com",
        "travelisfree.com", "ausbt.com.au", "executive-traveller.com",
        "headforpoints.com", "loungebuddy.com", "thedesignair.net",
        "seatguru.com", "airlinequality.com", "joshcahill.com",
    ],
}

def _domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""

def source_tier(url: str) -> int:
    d = _domain(url)
    for tier, domains in SOURCE_TIERS.items():
        if any(d == dom or d.endswith("."+dom) for dom in domains):
            return tier
    return 3

TIER_LABELS = {1: "Press", 2: "Creator", 3: "General"}


# ── IFE keyword gate ──────────────────────────────────────────────────────────
IFE_TITLE_KEYWORDS = [
    "inflight entertainment", "in-flight entertainment", "in flight entertainment",
    "ife system", "ife review", "ife ",
    "panasonic ex3", "panasonic ex2", "panasonic ex1", "panasonic astrova",
    "thales avant", "thales inflyt", "safran rave", "spi rave",
    "emirates ice", "viasat ife", "oryx one", "krisworld",
    "studiocx", "studioex", "planet ife", "collins venue",
    "seatback entertainment", "seatback screen", "seatback display",
    "airline entertainment review", "flight entertainment system",
    "4k ife", "4k inflight", "oled inflight",
    # broader flight-review terms — nearly every cabin/seat review covers IFE
    "business class review", "first class review", "economy class review",
    "premium economy review", "cabin review", "seat review", "flight review",
    "entertainment screen", "video on demand", "seatback screen",
    "inflight wifi review", "airline wifi review", "starlink wifi flight",
    "gogo wifi", "ife award", "passenger choice award",
    "gogo avance", "anuvu", "immfly", "bluebox",
]


# ── IFE system detection ──────────────────────────────────────────────────────
IFE_SYSTEM_PATTERNS = {
    "Emirates ICE":        ["emirates ice", "information, communication, entertainment"],
    "Panasonic Astrova":   ["panasonic astrova", "astrova 4k", "astrova oled"],
    "Panasonic eX3":       ["panasonic ex3", "ex3 ife", "panasonic avionics ex3"],
    "Panasonic eX2":       ["panasonic ex2"],
    "Panasonic eX1":       ["panasonic ex1"],
    "Thales AVANT Up":     ["avant up", "thales avant up"],
    "Thales AVANT":        ["thales avant", "thales inflyt", "inflyt experience"],
    "Safran RAVE Ultra":   ["rave ultra", "safran rave ultra", "spi rave ultra"],
    "Safran RAVE":         ["safran rave", " rave ife", "safran passenger innovations",
                            " spi ife", "spi inflight", "spi entertainment"],
    "Collins Venue":       ["collins venue", "rockwell collins venue"],
    "Viasat (streaming)":  ["viasat"],
    "Inmarsat GX":         ["inmarsat gx", "gx aviation"],
    "Oryx One":            ["oryx one"],
    "KrisWorld":           ["krisworld"],
    "StudioCX":            ["studiocx", "studio cx"],
    "Lumexis FTTS":        ["lumexis", "ftts"],
    "Gogo Avance":         ["gogo avance", "gogo vision", "gogo inflight"],
    "Anuvu":               ["anuvu", "global eagle entertainment"],
    "Immfly":              ["immfly"],
    "Bluebox Wow":         ["bluebox wow", "bluebox aviation"],
}


# ── IFE feature detection ─────────────────────────────────────────────────────
IFE_FEATURE_KEYWORDS = {
    "entertainment_system": ["entertainment system", "ife", "in-flight entertainment", "seatback screen", "vod"],
    "content":              ["movies", "tv shows", "tv series", "music", "games", "podcasts", "content library"],
    "connectivity":         ["wifi", "wi-fi", "internet", "connectivity", "bluetooth", "starlink", "onair"],
    "4k_display":           ["4k", "4k display", "4k screen", "uhd", "oled", "amoled"],
    "quality":              ["resolution", "display", "picture quality", "1080p", "touchscreen", "hd screen"],
    "seat":                 ["seat", "recline", "legroom", "comfort", "headrest"],
    "usb_power":            ["usb", "usb-c", "charging", "power outlet", "ac outlet"],
    "bluetooth_audio":      ["bluetooth", "wireless headphones", "airpods", "bluetooth audio"],
}


# ── Airlines & aircraft ───────────────────────────────────────────────────────
AIRLINE_KEYWORDS = [
    "emirates", "qatar airways", "etihad", "lufthansa", "british airways",
    "singapore airlines", "cathay pacific", "ana", "japan airlines", "jal",
    "air france", "klm", "turkish airlines", "finnair", "air canada",
    "united airlines", "american airlines", "delta", "southwest", "alaska airlines",
    "air india", "china airlines", "korean air", "eva air", "thai airways",
    "virgin atlantic", "iberia", "tap air portugal", "swiss", "austrian airlines",
    "qantas", "air new zealand", "china eastern", "china southern", "hainan airlines",
    "level", "wizz air", "ryanair", "easyjet",
]

AIRCRAFT_KEYWORDS = [
    "787", "777", "737", "a350", "a380", "a330", "a321", "a320", "a220",
    "dreamliner", "airbus", "boeing", "737 max", "a321neo", "a350-900", "a350-1000",
    "777x", "787-9", "787-10",
]


# ── Structured spec extraction ────────────────────────────────────────────────
SPEC_PATTERNS = {
    "screen_size": [
        r'(\d{1,2}(?:\.\d)?)[- ]?(?:inch|in\b|\")\s*(?:screen|display|monitor|touch)',
        r'(?:screen|display|monitor)\s+(?:is\s+)?(\d{1,2}(?:\.\d)?)[- ]?(?:inch|in\b|\")',
    ],
    "content_count": [
        r'(\d[\d,]+)\+?\s*(?:titles|movies|channels|hours? of content|content options|video options)',
        r'over\s+(\d[\d,]+)\s*(?:titles|movies|channels)',
        r'more than\s+(\d[\d,]+)\s*(?:titles|movies|channels)',
    ],
    "wifi_type": {
        "Starlink": ["starlink"],
        "Ka-band":  ["ka-band", "ka band", "inmarsat gx", "viasat ka"],
        "Ku-band":  ["ku-band", "ku band"],
        "Streaming":["streaming ife", "stream from your", "bring your own device", "byod"],
        "Wi-Fi":    ["wi-fi", "wifi", "on-board wifi"],
    },
    "controller": {
        "Touchscreen":       ["touchscreen", "touch screen", "touch-screen"],
        "Handheld remote":   ["handheld", "remote control", "handset"],
        "Trackpad":          ["trackpad", "track pad"],
        "Tablet":            ["tablet", "ipad"],
    },
}

def _extract_specs(text: str) -> dict:
    specs = {}
    t = text.lower()

    # Screen size — take the largest plausible value found
    sizes = []
    for pat in SPEC_PATTERNS["screen_size"]:
        for m in re.finditer(pat, t):
            try:
                v = float(m.group(1))
                if 6 <= v <= 32:          # sane IFE screen range
                    sizes.append(v)
            except ValueError:
                pass
    if sizes:
        specs["screen_size"] = f'{max(sizes):.0f}"'

    # Content count — take largest number found
    counts = []
    for pat in SPEC_PATTERNS["content_count"]:
        for m in re.finditer(pat, t):
            try:
                counts.append(int(m.group(1).replace(",", "")))
            except ValueError:
                pass
    if counts:
        c = max(counts)
        specs["content_count"] = f"{c:,}+"

    # WiFi type
    for label, keywords in SPEC_PATTERNS["wifi_type"].items():
        if any(kw in t for kw in keywords):
            specs["wifi_type"] = label
            break

    # Controller type
    for label, keywords in SPEC_PATTERNS["controller"].items():
        if any(kw in t for kw in keywords):
            specs["controller"] = label
            break

    return specs


# ── IFE system inference (airline + aircraft fallback) ───────────────────────
# Used when text-based detection finds nothing. Prefer airline-specific
# mappings; fall back to aircraft-type defaults.

AIRLINE_IFE_LOOKUP = {
    "emirates":          "Emirates ICE",
    "qatar airways":     "Oryx One",
    "singapore airlines":"KrisWorld",
    "cathay pacific":    "StudioCX",
    "ana":               "Panasonic eX3",
    "japan airlines":    "Panasonic eX3",
    "jal":               "Panasonic eX3",
    "lufthansa":         "Thales AVANT",
    "british airways":   "Panasonic eX3",
    "turkish airlines":  "Panasonic eX3",
    "finnair":           "Panasonic eX3",
    "air france":        "Thales AVANT",
    "klm":               "Thales AVANT",
    "etihad":            "Panasonic eX3",
    "air canada":        "Panasonic eX3",
    "united airlines":   "Panasonic eX3",
    "american airlines": "Panasonic eX3",
    "delta":             "Thales AVANT",
    "alaska airlines":   "Viasat (streaming)",
    "southwest":         "Viasat (streaming)",
    "china airlines":    "Panasonic eX3",
    "korean air":        "Panasonic eX3",
    "eva air":           "Panasonic eX3",
    "thai airways":      "Thales AVANT",
    "virgin atlantic":   "Thales AVANT",
    "iberia":            "Thales AVANT",
    "swiss":             "Thales AVANT",
    "austrian airlines": "Panasonic eX3",
    "qantas":            "Panasonic eX3",
    "air new zealand":   "Panasonic eX3",
    "china eastern":     "Thales AVANT",
    "china southern":    "Panasonic eX3",
    "hainan airlines":   "Thales AVANT",
    "air india":         "Panasonic eX3",
    "tap air portugal":  "Thales AVANT",
    # Safran RAVE operators
    "icelandair":        "Safran RAVE",
    "sun country":       "Safran RAVE",
    "volaris":           "Safran RAVE",
    "frontier":          "Safran RAVE",
    "allegiant":         "Safran RAVE",
}

AIRCRAFT_IFE_DEFAULTS = {
    "a380":    "Panasonic eX3",
    "a350":    "Panasonic eX3",
    "a330":    "Panasonic eX3",
    "a321neo": "Viasat (streaming)",
    "a321":    "Viasat (streaming)",
    "a320":    "Viasat (streaming)",
    "a220":    "Panasonic eX3",
    "787-10":  "Panasonic eX3",
    "787-9":   "Panasonic eX3",
    "787":     "Panasonic eX3",
    "777x":    "Panasonic Astrova",
    "777":     "Panasonic eX3",
    "737 max": "Viasat (streaming)",
    "737":     "Viasat (streaming)",
}


def infer_ife_system(airlines: list, aircraft: list) -> Optional[str]:
    """Return best-guess IFE system from airline/aircraft when text detection fails."""
    # 1. Airline lookup (most reliable — carriers rarely mix systems fleet-wide)
    for a in airlines:
        kw = a.get("keyword", "").lower()
        if kw in AIRLINE_IFE_LOOKUP:
            return AIRLINE_IFE_LOOKUP[kw]
    # 2. Aircraft fallback (longer keys first so 737 max matches before 737)
    ac_keywords = [a.get("keyword", "").lower() for a in aircraft]
    for key in sorted(AIRCRAFT_IFE_DEFAULTS, key=len, reverse=True):
        if any(key in ac for ac in ac_keywords):
            return AIRCRAFT_IFE_DEFAULTS[key]
    return None


# ── Known IFE reviewer YouTube channels ──────────────────────────────────────
# How to find a channel ID:
#   1. Go to the channel's YouTube page
#   2. Right-click → View Page Source
#   3. Ctrl+F → search for "channelId" — copy the 24-character UC... value
# Each channel search costs 100 API units, same as a keyword search.
KNOWN_IFE_CHANNELS: dict = {
    # Verified channel IDs — each costs 100 API units/day
    # To verify: channels?part=snippet&id=UC... (1 unit, batch up to 50)
    "Million Miles Marc":       "UCGZI_9g_4mWWZbTvO1N9Y4Q",  # verified ✓
    "ThemeParksandAttractions": "UCAzX7J8GbLSELJX4ecUI04A",  # verified ✓
    "Chris Films Things":       "UCIIotzUXweA445T6h8fBXRQ",  # verified ✓
    "theplanesguy":             "UClm9qlyx-E68Q3gGuaBj-SQ",  # verified ✓
    "From the Wing":            "UCOBUoOstpv-yCHZk2B77gXw",  # verified ✓
    "Nonstop Dan":              "UCLQ5XNN9iT4DmCbZXpy5Fdw",  # verified ✓
    "Simply Aviation":          "UCEF-9XhkdyFY0hMRUkmxXfQ",  # verified ✓
    "Eric Struk":               "UCDv-Fv9bAt-1bU9EBOnqHvw",  # verified ✓
    "Dennis Bunnik":            "UCQrk97MBH6DToctKRfQJcNQ",  # verified ✓ (DennisBunnik Travels)
    "iTripReport":              "UCujsRp13yioFAhhHZcEgkYw",  # verified ✓
}


# ── Search queries ────────────────────────────────────────────────────────────
AUTO_DISCOVERY_QUERIES = [
    '"inflight entertainment" review 2024',
    '"inflight entertainment" review 2025',
    '"inflight entertainment" review 2026',
    '"in-flight entertainment" IFE system review 2025',
    '"Panasonic Astrova" airline review',
    '"Panasonic eX3" airline review',
    '"Thales AVANT" airline review',
    '"Thales AVANT Up" airline inflight entertainment',
    '"Safran RAVE" inflight entertainment',
    '"Safran RAVE Ultra" IFE review',
    '"Safran Passenger Innovations" IFE',
    '"SPI RAVE" inflight entertainment',
    '"Emirates ICE" inflight entertainment',
    '"Oryx One" Qatar inflight entertainment',
    '"KrisWorld" Singapore Airlines entertainment',
    'airline IFE system review 2024',
    'airline IFE system review 2025',
    'airline IFE system review 2026',
    'seatback entertainment system airline review 2025',
    '"4K inflight entertainment" review',
    '"Panasonic Astrova" 4K OLED IFE',
    'Starlink inflight wifi airline 2024',
    'Starlink inflight wifi airline 2025',
    '"best inflight entertainment" airline award 2024',
    '"best inflight entertainment" airline award 2025',
    'APEX passenger choice award inflight entertainment 2024',
    'APEX passenger choice award inflight entertainment 2025',
    '"Gogo Avance" airline inflight entertainment',
    '"Anuvu" inflight entertainment airline',
    'new inflight entertainment system airline launch 2024',
    'new inflight entertainment system airline launch 2025',
    'aircraft interiors expo IFE system 2024',
    'airline wifi Starlink passenger review 2025',
]

YOUTUBE_QUERIES = [
    # IFE system-specific
    "Panasonic Astrova inflight entertainment review",
    "Panasonic eX3 inflight entertainment review",
    "Thales AVANT inflight entertainment review",
    "Thales AVANT Up inflight entertainment review",
    "Emirates ICE inflight entertainment review",
    "Safran RAVE IFE review",
    "Safran RAVE Ultra inflight entertainment",
    "Safran Passenger Innovations IFE",
    "SPI RAVE Ultra airline review",
    "Oryx One Qatar inflight entertainment review",
    "KrisWorld Singapore Airlines entertainment review",
    "StudioCX Cathay Pacific entertainment review",
    "Collins Venue IFE review",
    "Gogo Avance inflight wifi review",
    "Anuvu inflight entertainment system review",
    "Viasat inflight wifi airline speed test",
    "Inmarsat GX aviation wifi review",
    # Business/first class
    "Emirates A380 first class review",
    "Emirates 777 business class inflight entertainment",
    "Qatar Airways Qsuite inflight entertainment 2024",
    "Qatar Airways A350 business class review 2025",
    "Singapore Airlines business class inflight entertainment review",
    "Cathay Pacific A350 business class inflight entertainment",
    "ANA 787 business class inflight entertainment review",
    "Japan Airlines A350 business class review",
    "Lufthansa A350 business class inflight entertainment",
    "British Airways Club World inflight entertainment review",
    "Turkish Airlines business class inflight entertainment review",
    "Air France B777 business class RAVE Ultra review",
    "Virgin Atlantic A350 first class RAVE Ultra review",
    "Finnair A350 business class inflight entertainment",
    "Delta One business class inflight entertainment review",
    "United Polaris inflight entertainment review",
    "American Airlines business class inflight entertainment",
    "Etihad A350 business class inflight entertainment",
    "Korean Air business class inflight entertainment review",
    "Qantas A380 business class inflight entertainment",
    "Icelandair inflight entertainment RAVE review",
    "Air India business class inflight entertainment review",
    "Oman Air business class inflight entertainment review",
    # Economy class
    "Emirates economy class inflight entertainment review",
    "Qatar Airways economy class inflight entertainment review",
    "Singapore Airlines economy class inflight entertainment review",
    "British Airways economy class inflight entertainment review",
    "Air France economy class inflight entertainment review",
    "Turkish Airlines economy class inflight entertainment review",
    "Delta economy class inflight entertainment review",
    "United economy class inflight entertainment review",
    "Virgin Atlantic economy class inflight entertainment review",
    # Premium economy
    "Emirates premium economy inflight entertainment review",
    "Qatar Airways premium economy inflight entertainment review",
    "Air France premium economy inflight entertainment review",
    "Delta Premium Select inflight entertainment review",
    "United Premium Plus inflight entertainment review",
    # Starlink & WiFi
    "Alaska Airlines Starlink wifi review",
    "Delta Starlink inflight wifi review",
    "Air New Zealand Starlink inflight wifi review",
    "airline inflight wifi speed test 2025",
    # Aircraft-specific
    "A380 inflight entertainment seatback review",
    "A350 inflight entertainment system review",
    "Boeing 787 inflight entertainment review",
    "Boeing 777 inflight entertainment review",
    "A321neo inflight entertainment review",
    # Industry & awards
    "best airline inflight entertainment 2024",
    "best airline inflight entertainment 2025",
    "APEX passenger choice award inflight entertainment",
    "new inflight entertainment system launch 2025",
    # General
    "inflight entertainment IFE review 2023",
    "inflight entertainment IFE review 2024",
    "inflight entertainment IFE review 2025",
    "4K inflight entertainment seatback review",
    "OLED inflight entertainment review",
]

# Known trusted source URLs to scrape directly (Tier 1 targets)
TRUSTED_SOURCES = [
    "https://simpleflying.com/?s=inflight+entertainment+2025",
    "https://simpleflying.com/?s=IFE+system+2025",
    "https://airlinegeeks.com/?s=inflight+entertainment",
    "https://thepointsguy.com/search?q=inflight+entertainment+2025",
]


class IFECrawler:
    """
    Auto-discovery crawler for IFE reviews.
    - Keyword-gates all results on title or description
    - Scores sources by reputation tier (Press / Creator / General)
    - Extracts structured specs: screen size, content count, WiFi type, controller
    - Targets 2025-2026 content primarily
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, verify_ssl: bool = False, api_key: str = ""):
        self.verify_ssl = verify_ssl
        self.api_key = api_key
        self.visited: set = set()
        self.results: List[dict] = []
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # ── Public API ────────────────────────────────────────────────────────────

    def auto_discover(self, existing_urls: set = None, max_results: int = 500, days_lookback: int = None) -> List[dict]:
        self.results = []
        if existing_urls:
            self.visited.update(existing_urls)

        published_after = None
        if days_lookback:
            from datetime import datetime, timedelta, timezone
            dt = datetime.now(timezone.utc) - timedelta(days=days_lookback)
            published_after = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        if self.api_key:
            # Collect all video IDs across every query (50 results each = ~2,000 candidates)
            all_ids: List[str] = []
            seen_ids: set = set()
            for query in YOUTUBE_QUERIES:
                ids = self._yt_search_api(query, limit=50, published_after=published_after)
                for vid_id in ids:
                    if vid_id not in seen_ids:
                        url = f"https://www.youtube.com/watch?v={vid_id}"
                        if url not in self.visited:
                            seen_ids.add(vid_id)
                            all_ids.append(vid_id)

            # Also pull recent uploads from every known IFE reviewer channel directly
            for channel_name, channel_id in KNOWN_IFE_CHANNELS.items():
                ids = self._yt_search_channel(channel_id, limit=50, published_after=published_after)
                for vid_id in ids:
                    if vid_id not in seen_ids:
                        url = f"https://www.youtube.com/watch?v={vid_id}"
                        if url not in self.visited:
                            seen_ids.add(vid_id)
                            all_ids.append(vid_id)

            # Batch-fetch structured metadata (1 API unit per 50 videos)
            details = self._yt_fetch_details(all_ids)

            for vid_id in all_ids:
                if len(self.results) >= max_results:
                    break
                item = details.get(vid_id)
                if not item:
                    continue
                url = f"https://www.youtube.com/watch?v={vid_id}"
                self.visited.add(url)
                entry = self._build_youtube_entry_from_api(vid_id, item)
                if entry:
                    self.results.append(entry)
        else:
            # Fallback: scrape YouTube search page + DDG
            for query in YOUTUBE_QUERIES:
                if len(self.results) >= max_results:
                    break
                video_ids = self._yt_search(query, limit=10)
                if not video_ids:
                    video_ids = self._ddg_search_youtube(query + " site:youtube.com", limit=8)
                for vid_id in video_ids:
                    if len(self.results) >= max_results:
                        break
                    url = f"https://www.youtube.com/watch?v={vid_id}"
                    if url in self.visited:
                        continue
                    self.visited.add(url)
                    entry = self._fetch_youtube(vid_id, url)
                    if entry:
                        self.results.append(entry)
                time.sleep(1.2)

        # Article pages via DuckDuckGo (unchanged)
        for query in AUTO_DISCOVERY_QUERIES:
            if len(self.results) >= max_results:
                break
            article_urls = self._ddg_search_articles(query, limit=4)
            for url in article_urls:
                if len(self.results) >= max_results:
                    break
                if url in self.visited:
                    continue
                self.visited.add(url)
                entry = self._fetch_article(url)
                if entry:
                    self.results.append(entry)
            time.sleep(1.2)

        return self.results

    def crawl_review_sites(self, airline=None, aircraft=None):
        return self.auto_discover()

    def save_results(self, path="ife_results.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

    # ── DuckDuckGo search ─────────────────────────────────────────────────────

    def _ddg_post(self, query: str) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query, "b": "", "kl": "us-en"},
                timeout=14,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception:
            return None

    def _yt_search(self, query: str, limit: int = 10) -> List[str]:
        """Scrape YouTube search results directly — much higher yield than DDG site: queries."""
        import json as _json
        try:
            encoded = requests.utils.quote(query)
            resp = self.session.get(
                f"https://www.youtube.com/results?search_query={encoded}&sp=CAI%253D",
                timeout=14, verify=self.verify_ssl,
            )
            # YouTube embeds all search data as ytInitialData JSON in the page
            match = re.search(r'var ytInitialData\s*=\s*(\{.+?\});\s*(?:</script>|var )', resp.text, re.DOTALL)
            if not match:
                return []
            data = _json.loads(match.group(1))
            items = (
                data.get("contents", {})
                    .get("twoColumnSearchResultsRenderer", {})
                    .get("primaryContents", {})
                    .get("sectionListRenderer", {})
                    .get("contents", [{}])[0]
                    .get("itemSectionRenderer", {})
                    .get("contents", [])
            )
            ids = []
            for item in items:
                vid_id = item.get("videoRenderer", {}).get("videoId")
                if vid_id and vid_id not in ids:
                    ids.append(vid_id)
                    if len(ids) >= limit:
                        break
            return ids
        except Exception:
            return []

    def _yt_search_api(self, query: str, limit: int = 50, published_after: str = None) -> List[str]:
        """YouTube Data API v3 search — 100 quota units per call, up to 50 results."""
        params = {
            "part": "id",
            "q": query,
            "type": "video",
            "maxResults": min(limit, 50),
            "order": "relevance",
            "key": self.api_key,
        }
        if published_after:
            params["publishedAfter"] = published_after
        try:
            resp = self.session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=15,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            return [
                item["id"]["videoId"]
                for item in resp.json().get("items", [])
                if item.get("id", {}).get("videoId")
            ]
        except Exception:
            return []

    def _yt_search_channel(self, channel_id: str, limit: int = 50, published_after: str = None) -> List[str]:
        """Search within a specific channel — catches reviewers regardless of keyword matching."""
        params = {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "maxResults": min(limit, 50),
            "order": "date",
            "key": self.api_key,
        }
        if published_after:
            params["publishedAfter"] = published_after
        try:
            resp = self.session.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=15,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
            return [
                item["id"]["videoId"]
                for item in resp.json().get("items", [])
                if item.get("id", {}).get("videoId")
            ]
        except Exception:
            return []

    def _yt_fetch_details(self, video_ids: List[str]) -> Dict[str, dict]:
        """Batch-fetch snippet + statistics for up to 50 videos per call (1 quota unit each)."""
        details: Dict[str, dict] = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            try:
                resp = self.session.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "part": "snippet,statistics,contentDetails",
                        "id": ",".join(batch),
                        "key": self.api_key,
                    },
                    timeout=15,
                    verify=self.verify_ssl,
                )
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    details[item["id"]] = item
            except Exception:
                pass
        return details

    def _build_youtube_entry_from_api(self, video_id: str, item: dict) -> Optional[dict]:
        """Build a result entry from a YouTube Data API videos.list item."""
        snippet = item.get("snippet", {})
        title = snippet.get("title", "").strip()
        description = snippet.get("description", "").strip()

        if not self._has_ife_keyword(title) and not self._has_ife_keyword(description):
            return None

        published_at = snippet.get("publishedAt", "")
        try:
            year = int(published_at[:4])
        except (ValueError, IndexError):
            year = self._year_from_text(title + " " + description) or 2025

        url = f"https://www.youtube.com/watch?v={video_id}"
        combined = (title + " " + description).lower()

        trans_ok, excerpt, captions, full_transcript = False, None, [], ""
        if TRANSCRIPTS_AVAILABLE:
            trans_ok, excerpt, captions, full_transcript = self._get_transcript(video_id)

        search_text = combined + " " + full_transcript
        airlines_m = self._mentions(search_text, AIRLINE_KEYWORDS)
        aircraft_m = self._mentions(search_text, AIRCRAFT_KEYWORDS)
        detected = self._detect_system(search_text)
        inferred = False
        if not detected:
            detected = infer_ife_system(airlines_m, aircraft_m)
            inferred = detected is not None

        stats = item.get("statistics", {})
        return {
            "url":                  url,
            "title":                title[:150],
            "year":                 year,
            "published_at":         published_at,
            "channel_title":        snippet.get("channelTitle", ""),
            "view_count":           int(stats.get("viewCount", 0) or 0),
            "ife_system":           detected,
            "ife_system_inferred":  inferred,
            "media_type":           "video",
            "airlines_mentioned":   airlines_m,
            "aircraft_mentioned":   aircraft_m,
            "ife_features":         self._features(search_text),
            "ife_specs":            _extract_specs(search_text),
            "transcript_available": trans_ok,
            "transcript_excerpt":   excerpt,
            "captions":             captions,
            "source_tier":          2,
            "source_name":          "YouTube",
        }

    def _ddg_search_youtube(self, query: str, limit: int = 5) -> List[str]:
        """Fallback: DDG site:youtube.com search (sparse but works without JS)."""
        soup = self._ddg_post(query)
        if not soup:
            return []
        ids = []
        for a in soup.select("a.result__url, a.result__a"):
            href = a.get("href", "")
            vid_id = self._extract_yt_id(href)
            if vid_id and vid_id not in ids:
                ids.append(vid_id)
                if len(ids) >= limit:
                    break
        return ids

    def _ddg_search_articles(self, query: str, limit: int = 4) -> List[str]:
        soup = self._ddg_post(query)
        if not soup:
            return []
        urls = []
        skip = {"youtube.com", "twitter.com", "facebook.com", "instagram.com",
                "tiktok.com", "reddit.com", "wikipedia.org"}
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            url = self._resolve_ddg(href)
            if not url:
                continue
            if any(s in url for s in skip):
                continue
            if url not in urls:
                urls.append(url)
                if len(urls) >= limit:
                    break
        return urls

    def _resolve_ddg(self, href: str) -> Optional[str]:
        if "//duckduckgo.com/l/?" in href:
            try:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse("https:" + href).query)
                uddg = qs.get("uddg", [None])[0]
                return urllib.parse.unquote(uddg) if uddg else None
            except Exception:
                return None
        if href.startswith("http"):
            return href
        return None

    def _extract_yt_id(self, text: str) -> Optional[str]:
        m = re.search(r"(?:v=|youtu\.be/|/embed/|/v/|/shorts/)([A-Za-z0-9_-]{11})", text)
        return m.group(1) if m else None

    # ── YouTube fetch ─────────────────────────────────────────────────────────

    def _fetch_youtube(self, video_id: str, url: str) -> Optional[dict]:
        try:
            resp = self.session.get(url, timeout=12, verify=self.verify_ssl)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title = (soup.title.string or "").replace(" - YouTube", "").strip()
            desc_meta = (
                soup.find("meta", {"name": "description"}) or
                soup.find("meta", {"property": "og:description"})
            )
            description = desc_meta["content"].strip() if desc_meta and desc_meta.get("content") else ""

            if not self._has_ife_keyword(title) and not self._has_ife_keyword(description):
                return None

            combined = (title + " " + description).lower()
            year = self._year_from_text(combined) or 2025

            trans_ok, excerpt, captions = False, None, []
            full_transcript = ""
            if TRANSCRIPTS_AVAILABLE:
                trans_ok, excerpt, captions, full_transcript = self._get_transcript(video_id)

            search_text = combined + " " + full_transcript
            airlines_m  = self._mentions(search_text, AIRLINE_KEYWORDS)
            aircraft_m  = self._mentions(search_text, AIRCRAFT_KEYWORDS)
            detected    = self._detect_system(search_text)
            inferred    = False
            if not detected:
                detected = infer_ife_system(airlines_m, aircraft_m)
                inferred = detected is not None

            return {
                "url":                  url,
                "title":                title[:150],
                "year":                 year,
                "ife_system":           detected,
                "ife_system_inferred":  inferred,
                "media_type":           "video",
                "airlines_mentioned":   airlines_m,
                "aircraft_mentioned":   aircraft_m,
                "ife_features":         self._features(search_text),
                "ife_specs":            _extract_specs(search_text),
                "transcript_available": trans_ok,
                "transcript_excerpt":   excerpt,
                "captions":             captions,
                "source_tier":          2,
                "source_name":          "YouTube",
            }
        except Exception:
            return None

    def _get_transcript(self, video_id: str):
        try:
            api = YouTubeTranscriptApi()
            try:
                fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
            except Exception:
                # Fall back to auto-generated captions (YouTube generates these for most videos)
                tlist = api.list(video_id)
                fetched = tlist.find_generated_transcript(["en"]).fetch()
            segs = [{"text": s.text, "start": s.start} for s in fetched]
            if not segs:
                return False, None, [], ""
            full = " ".join(s["text"] for s in segs)

            # Keywords used to score each segment for IFE relevance
            score_kws = (
                [kw for kws in IFE_FEATURE_KEYWORDS.values() for kw in kws]
                + [p for patterns in IFE_SYSTEM_PATTERNS.values() for p in patterns]
            )

            def seg_score(idx):
                # 3-segment sliding window for context
                chunk = " ".join(
                    segs[j]["text"]
                    for j in range(max(0, idx - 1), min(len(segs), idx + 2))
                ).lower()
                return sum(1 for kw in score_kws if kw in chunk)

            # Pick top 5 IFE-relevant segments, spaced at least 15 segments apart
            order = sorted(range(len(segs)), key=lambda i: -seg_score(i))
            chosen_idx = []
            for i in order:
                if seg_score(i) == 0:
                    break
                if not any(abs(i - j) < 15 for j in chosen_idx):
                    chosen_idx.append(i)
                if len(chosen_idx) >= 5:
                    break

            # Fill with evenly-spaced segments if fewer than 5 IFE hits
            if len(chosen_idx) < 5:
                step = max(1, len(segs) // 5)
                for k in range(0, min(len(segs), step * 5), step):
                    if not any(abs(k - j) < 5 for j in chosen_idx) and len(chosen_idx) < 5:
                        chosen_idx.append(k)

            chosen_idx.sort()  # chronological order for display

            # Excerpt = the single highest-scoring segment (most IFE-relevant quote)
            best_seg = segs[order[0]] if order else segs[0]
            best_text = best_seg["text"].strip()
            excerpt = best_text + ("…" if len(full) > len(best_text) else "")

            caps = []
            for i in chosen_idx[:5]:
                s = segs[i]
                raw = int(s["start"])
                m, sec = raw // 60, raw % 60
                caps.append({
                    "timestamp":     f"{m}:{sec:02d}",
                    "start_seconds": raw,
                    "text":          s["text"].strip(),
                })

            return True, excerpt, caps, full
        except Exception:
            return False, None, [], ""

    # ── Article fetch ─────────────────────────────────────────────────────────

    def _fetch_article(self, url: str) -> Optional[dict]:
        # Only accept articles from known aviation press (T1) or creator blogs (T2).
        # General/unknown sites (T3) are excluded — internal sources cover those.
        tier = source_tier(url)
        if tier == 3:
            return None

        try:
            resp = self.session.get(url, timeout=10, verify=self.verify_ssl)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title = (soup.title.string or "").strip()
            desc_meta = (
                soup.find("meta", {"name": "description"}) or
                soup.find("meta", {"property": "og:description"})
            )
            description = desc_meta["content"].strip() if desc_meta and desc_meta.get("content") else ""

            if not self._has_ife_keyword(title) and not self._has_ife_keyword(description):
                return None

            text       = soup.get_text(separator=" ").lower()
            year       = self._year_from_meta(soup) or self._year_from_text(text) or 2025
            airlines_m = self._mentions(text, AIRLINE_KEYWORDS)
            aircraft_m = self._mentions(text, AIRCRAFT_KEYWORDS)
            detected   = self._detect_system(text)
            inferred   = False
            if not detected:
                detected = infer_ife_system(airlines_m, aircraft_m)
                inferred = detected is not None

            return {
                "url":                  url,
                "title":                title[:150],
                "year":                 year,
                "ife_system":           detected,
                "ife_system_inferred":  inferred,
                "media_type":           "article",
                "airlines_mentioned":   airlines_m,
                "aircraft_mentioned":   aircraft_m,
                "ife_features":         self._features(text),
                "ife_specs":            _extract_specs(text),
                "transcript_available": False,
                "transcript_excerpt":   None,
                "captions":             [],
                "source_tier":          tier,
                "source_name":        TIER_LABELS[tier],
            }
        except Exception:
            return None

    # ── Text helpers ──────────────────────────────────────────────────────────

    def _has_ife_keyword(self, text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in IFE_TITLE_KEYWORDS)

    def _detect_system(self, text: str) -> Optional[str]:
        t = text.lower()
        for name, patterns in IFE_SYSTEM_PATTERNS.items():
            if any(p in t for p in patterns):
                return name
        return None

    def _features(self, text: str) -> Dict[str, bool]:
        return {f: True for f, kws in IFE_FEATURE_KEYWORDS.items() if any(kw in text for kw in kws)}

    def _mentions(self, text: str, keywords: List[str]) -> List[Dict]:
        out = [{"keyword": kw, "mentions": text.count(kw)} for kw in keywords if kw in text]
        return sorted(out, key=lambda x: x["mentions"], reverse=True)[:5]

    def _year_from_meta(self, soup: BeautifulSoup) -> Optional[int]:
        for attr in ("article:published_time", "datePublished", "publish_date", "date"):
            meta = soup.find("meta", {"property": attr}) or soup.find("meta", {"name": attr})
            if meta and meta.get("content"):
                m = re.search(r"(202[0-9])", meta["content"])
                if m:
                    return int(m.group(1))
        return None

    def _year_from_text(self, text: str) -> Optional[int]:
        # Prefer most recent year found
        for y in ["2026", "2025", "2024", "2023", "2022"]:
            if y in text:
                return int(y)
        m = re.search(r"(202[0-9])", text)
        return int(m.group(1)) if m else None
