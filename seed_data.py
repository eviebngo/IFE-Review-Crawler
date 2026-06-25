#!/usr/bin/env python3
"""
Seed script to populate initial IFE review data (2022-2023).
Fields: factual only — no sentiment or relevance scoring.
Includes transcript availability and caption excerpts.
"""
import json
from datetime import datetime

SEED_REVIEWS = [
    {
        "url": "https://www.seatguru.com/airlines/united-airlines",
        "title": "United Airlines Boeing 787 Dreamliner IFE Experience",
        "year": 2023,
        "ife_system": "Panasonic eX3",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "united", "mentions": 12},
            {"keyword": "american", "mentions": 3}
        ],
        "aircraft_mentioned": [
            {"keyword": "787", "mentions": 8}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "connectivity": True,
            "quality": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=ivSAn7IT2Zg",
        "title": "Introducing ICE: Emirates In-Flight Entertainment System",
        "year": 2023,
        "ife_system": "Emirates ICE",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "emirates", "mentions": 15}
        ],
        "aircraft_mentioned": [
            {"keyword": "a380", "mentions": 10}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "connectivity": True,
            "quality": True,
            "seat": True
        },
        "transcript_available": True,
        "transcript_excerpt": "The ICE system on the A380 features a 23-inch widescreen monitor in first class with over 6,500 channels including movies, TV series, music, and games.",
        "captions": [
            {"timestamp": "0:42", "text": "So here we have the ICE touchscreen — that stands for Information, Communication, Entertainment."},
            {"timestamp": "1:15", "text": "Over 6,500 channels of content available on this flight. The screen is 23 inches with really good resolution."},
            {"timestamp": "3:08", "text": "The noise-cancelling headsets they hand out are genuinely decent. Not Bose, but solid."}
        ]
    },
    {
        "url": "https://www.seatguru.com/airlines/delta-airlines",
        "title": "Delta Airlines Boeing 777 WiFi and Entertainment Review",
        "year": 2023,
        "ife_system": "Panasonic eX2",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "delta", "mentions": 9},
            {"keyword": "southwest", "mentions": 2}
        ],
        "aircraft_mentioned": [
            {"keyword": "777", "mentions": 7}
        ],
        "ife_features": {
            "entertainment_system": True,
            "connectivity": True,
            "content": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=xhxqIofWbvY",
        "title": "Singapore Airlines KrisWorld Inflight Entertainment System",
        "year": 2022,
        "ife_system": "Panasonic eX3",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "singapore airlines", "mentions": 11}
        ],
        "aircraft_mentioned": [
            {"keyword": "a350", "mentions": 9}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "quality": True,
            "seat": True,
            "connectivity": True
        },
        "transcript_available": True,
        "transcript_excerpt": "KrisWorld on the A350 is powered by Panasonic eX3. The 18-inch 1080p screen is responsive and the content library — over 1,800 movies — is one of the largest in the industry.",
        "captions": [
            {"timestamp": "0:30", "text": "KrisWorld, Singapore Airlines' own branded IFE, runs on the Panasonic eX3 platform."},
            {"timestamp": "2:10", "text": "18-inch touchscreen, very fast response, and USB-A plus USB-C power on every seat."},
            {"timestamp": "4:45", "text": "The content depth is exceptional — 1,800 movies, 27 audio channels, and full Bluetooth headphone pairing."}
        ]
    },
    {
        "url": "https://www.trustpilot.com/review/british-airways",
        "title": "British Airways 787 Dreamliner Entertainment Issues 2022",
        "year": 2022,
        "ife_system": "Thales AVANT",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "british airways", "mentions": 8}
        ],
        "aircraft_mentioned": [
            {"keyword": "787", "mentions": 6}
        ],
        "ife_features": {
            "entertainment_system": True,
            "quality": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=fZiaWBQZFKE",
        "title": "Most Modern Ever? Entertainment System Onboard Lufthansa Airbus A350",
        "year": 2022,
        "ife_system": "Thales AVANT",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "lufthansa", "mentions": 10}
        ],
        "aircraft_mentioned": [
            {"keyword": "boeing", "mentions": 5},
            {"keyword": "777", "mentions": 4}
        ],
        "ife_features": {
            "entertainment_system": True,
            "quality": True
        },
        "transcript_available": True,
        "transcript_excerpt": "Lufthansa's Thales AVANT system offers a 15.4-inch screen in business class. Touch response is average — the remote handset is more reliable.",
        "captions": [
            {"timestamp": "1:00", "text": "The AVANT system here — you've got a 15.4-inch screen, which frankly is on the smaller end for business class in 2022."},
            {"timestamp": "2:33", "text": "Touch is a bit laggy. The remote handset on the armrest actually works better."},
            {"timestamp": "5:10", "text": "Content library: about 300 movies and a handful of TV shows. Not the deepest catalog."}
        ]
    },
    {
        "url": "https://www.seatguru.com/airlines/cathay-pacific",
        "title": "Cathay Pacific A350 StudioCX IFE Entertainment Guide",
        "year": 2023,
        "ife_system": "Panasonic eX3",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "cathay pacific", "mentions": 12}
        ],
        "aircraft_mentioned": [
            {"keyword": "a350", "mentions": 8}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "connectivity": True,
            "quality": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.skytrax.com/airline-reviews/american-airlines",
        "title": "American Airlines Boeing 777 WiFi and Seatback Entertainment",
        "year": 2023,
        "ife_system": "Panasonic eX2",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "american", "mentions": 11},
            {"keyword": "united", "mentions": 2}
        ],
        "aircraft_mentioned": [
            {"keyword": "777", "mentions": 7},
            {"keyword": "787", "mentions": 3}
        ],
        "ife_features": {
            "entertainment_system": True,
            "connectivity": True,
            "content": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=l6HyxzcjAz0",
        "title": "How's Emirates Doing in 2022? A380 Economy Class Review",
        "year": 2022,
        "ife_system": "Emirates ICE",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "emirates", "mentions": 13},
            {"keyword": "qatar airways", "mentions": 4}
        ],
        "aircraft_mentioned": [
            {"keyword": "a380", "mentions": 8}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "quality": True
        },
        "transcript_available": True,
        "transcript_excerpt": "Comparing Emirates ICE to Qatar Oryx One: ICE wins on content volume, Oryx One on screen sharpness and touch responsiveness.",
        "captions": [
            {"timestamp": "0:55", "text": "ICE: 6,500+ channels. Oryx One: about 4,000. ICE takes the content volume trophy easily."},
            {"timestamp": "3:22", "text": "But touch sensitivity — Qatar's Thales AVANT is much snappier. Emirates lags noticeably."},
            {"timestamp": "6:10", "text": "Both have live TV and moving map. Emirates' map is more detailed; Qatar's UI is cleaner."}
        ]
    },
    {
        "url": "https://www.trustpilot.com/review/southwest-airlines",
        "title": "Southwest Airlines Streaming Entertainment on Boeing 737",
        "year": 2023,
        "ife_system": "Viasat (streaming)",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "southwest", "mentions": 9}
        ],
        "aircraft_mentioned": [
            {"keyword": "boeing", "mentions": 6}
        ],
        "ife_features": {
            "entertainment_system": True,
            "connectivity": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=OTZ8vriLMkM",
        "title": "Qatar Airways Inflight Entertainment System Review — Oryx One on A350",
        "year": 2023,
        "ife_system": "Thales AVANT",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "qatar airways", "mentions": 14}
        ],
        "aircraft_mentioned": [
            {"keyword": "a350", "mentions": 10}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "connectivity": True,
            "quality": True,
            "seat": True
        },
        "transcript_available": True,
        "transcript_excerpt": "Oryx One runs on Thales AVANT with a 17-inch 4K display in business class. Content: 4,000+ options including new releases within 90 days of theatrical.",
        "captions": [
            {"timestamp": "0:10", "text": "Oryx One — Qatar's IFE brand — powered by Thales AVANT."},
            {"timestamp": "1:44", "text": "17-inch 4K screen in Qsuite. Colors are vivid and the touch response is the fastest I've tested in this category."},
            {"timestamp": "4:00", "text": "New movie releases within 90 days of theatrical run. That's significantly faster than most competitors."}
        ]
    },
    {
        "url": "https://www.airlinequality.com/airline-reviews/air-france",
        "title": "Air France A330 Entertainment System Review 2022",
        "year": 2022,
        "ife_system": "Thales AVANT",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "air france", "mentions": 10}
        ],
        "aircraft_mentioned": [
            {"keyword": "a330", "mentions": 7}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "quality": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=hwLzO7T5s5A",
        "title": "ANA All Nippon Airways — Japan Elevated: In-Flight Entertainment",
        "year": 2022,
        "ife_system": "Panasonic eX3",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "ana", "mentions": 11}
        ],
        "aircraft_mentioned": [
            {"keyword": "777", "mentions": 8}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "connectivity": True,
            "quality": True
        },
        "transcript_available": True,
        "transcript_excerpt": "ANA's 777 runs the Panasonic eX3 with a 15.4-inch screen in economy. The system boots quickly and the Japanese content catalog is extensive.",
        "captions": [
            {"timestamp": "0:22", "text": "Panasonic eX3 here, same platform as Singapore's KrisWorld but with ANA's own content interface."},
            {"timestamp": "2:05", "text": "Boot time is about 45 seconds from power-on to main menu. Fast."},
            {"timestamp": "5:30", "text": "The Japanese film and TV catalog is the deepest I've seen on any non-Japanese carrier."}
        ]
    },
    {
        "url": "https://reddit.com/r/flying/comments/jal-review-2022",
        "title": "Japan Airlines A350 IFE — Panasonic eX3 Review",
        "year": 2022,
        "ife_system": "Panasonic eX3",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "japan airlines", "mentions": 13},
            {"keyword": "ana", "mentions": 3}
        ],
        "aircraft_mentioned": [
            {"keyword": "a350", "mentions": 9},
            {"keyword": "787", "mentions": 4}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "quality": True,
            "connectivity": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=GTQSqTEflxs",
        "title": "Turkish Airlines Airbus A350-900 Inflight Entertainment System",
        "year": 2023,
        "ife_system": "Panasonic eX3",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "turkish airlines", "mentions": 12}
        ],
        "aircraft_mentioned": [
            {"keyword": "787", "mentions": 7}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "connectivity": True,
            "quality": True
        },
        "transcript_available": True,
        "transcript_excerpt": "PLANET is Turkish Airlines' IFE brand on the 787, built on Panasonic eX3. Offers 350+ movies and an expanding Turkish content section.",
        "captions": [
            {"timestamp": "0:35", "text": "PLANET — Turkish Airlines' branding for their Panasonic eX3 system. 16-inch screen in business."},
            {"timestamp": "2:50", "text": "350+ movies, solid Turkish TV selection, and a surprisingly large international music library."},
            {"timestamp": "6:15", "text": "Wi-Fi connectivity via Ku-band. Speeds were adequate for messaging, not great for streaming."}
        ]
    },
    {
        "url": "https://www.skytrax.com/airline-reviews/air-canada",
        "title": "Air Canada 787 IFE System — Content and Connectivity 2023",
        "year": 2023,
        "ife_system": "Panasonic eX2",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "air canada", "mentions": 9}
        ],
        "aircraft_mentioned": [
            {"keyword": "787", "mentions": 6}
        ],
        "ife_features": {
            "entertainment_system": True,
            "connectivity": True,
            "content": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=H89Sbjgb-_Q",
        "title": "Thales InFlyt Entertainment — The AVANT Passenger Experience",
        "year": 2022,
        "ife_system": "Thales AVANT",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "klm", "mentions": 10}
        ],
        "aircraft_mentioned": [
            {"keyword": "787", "mentions": 7}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "connectivity": True
        },
        "transcript_available": True,
        "transcript_excerpt": "KLM's 787 runs Thales AVANT with a 12-inch economy screen. The UI is clean and Netflix-style browsing makes content discovery easy.",
        "captions": [
            {"timestamp": "0:50", "text": "KLM went with Thales AVANT for the 787. 12-inch economy screen — smaller than the competition."},
            {"timestamp": "2:40", "text": "The UI is actually really clean. Browsing by genre, mood, or duration makes it easy to find something."},
            {"timestamp": "4:55", "text": "USB-A charging only in economy — no USB-C, which is a miss in 2022."}
        ]
    },
    {
        "url": "https://reddit.com/r/travel/comments/etihad-review",
        "title": "Etihad Airways A380 E-Box IFE System Review 2022",
        "year": 2022,
        "ife_system": "Panasonic eX2",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "etihad", "mentions": 11}
        ],
        "aircraft_mentioned": [
            {"keyword": "a380", "mentions": 8}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "quality": True,
            "seat": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.trustpilot.com/review/alaska-airlines",
        "title": "Alaska Airlines 737 MAX Streaming IFE — Viasat WiFi 2023",
        "year": 2023,
        "ife_system": "Viasat (streaming)",
        "media_type": "article",
        "airlines_mentioned": [
            {"keyword": "alaska airlines", "mentions": 8}
        ],
        "aircraft_mentioned": [
            {"keyword": "737", "mentions": 6}
        ],
        "ife_features": {
            "entertainment_system": True,
            "connectivity": True
        },
        "transcript_available": False,
        "transcript_excerpt": None,
        "captions": []
    },
    {
        "url": "https://www.youtube.com/watch?v=TbnSNr5Bm-Y",
        "title": "Finnair Long-Haul Inflight Entertainment System — Elevated Experience",
        "year": 2023,
        "ife_system": "Panasonic eX3",
        "media_type": "video",
        "airlines_mentioned": [
            {"keyword": "finnair", "mentions": 10}
        ],
        "aircraft_mentioned": [
            {"keyword": "a350", "mentions": 8}
        ],
        "ife_features": {
            "entertainment_system": True,
            "content": True,
            "quality": True,
            "connectivity": True
        },
        "transcript_available": True,
        "transcript_excerpt": "Finnair's A350 uses Panasonic eX3 with a 13.3-inch economy screen. Strong Nordic content selection; Bluetooth audio pairing available at every seat.",
        "captions": [
            {"timestamp": "0:20", "text": "Finnair A350 — Panasonic eX3 platform. 13.3-inch screen in economy, decent size."},
            {"timestamp": "2:10", "text": "Bluetooth headphone pairing at every seat — that's still uncommon in economy and really appreciated."},
            {"timestamp": "4:40", "text": "Nordic content selection: Finnish, Swedish, Norwegian films and TV. Solid if you're into that."}
        ]
    }
]


def seed_database():
    """Create the cache file from SEED_REVIEWS."""
    cache_file = "ife_cache.json"
    cache_data = {
        "reviews": SEED_REVIEWS,
        "last_updated": datetime.now().isoformat()
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)

    ife_systems = sorted(set(r["ife_system"] for r in SEED_REVIEWS))
    with_transcript = sum(1 for r in SEED_REVIEWS if r["transcript_available"])
    print(f"Seeded {len(SEED_REVIEWS)} reviews to {cache_file}")
    print(f"  Years: 2022-2023")
    print(f"  IFE Systems: {', '.join(ife_systems)}")
    print(f"  With transcripts/captions: {with_transcript}")


if __name__ == "__main__":
    seed_database()
