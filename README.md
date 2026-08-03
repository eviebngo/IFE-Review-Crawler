# IFE Review Database

This is my Summer 2026 IFE Review Database project! Feel free to clone this repo and make edits on your own. Happy researching!

A self-hosted competitive-intelligence platform for airline **in-flight entertainment (IFE)**. It continuously collects public YouTube reviews (plus press articles), reads what reviewers actually say — including full transcripts — and turns it into a browsable, filterable dashboard: which airlines run which IFE systems, which features people talk about (4K screens, Bluetooth audio, moving map, tail camera, watch party…), what's trending, and what viewers think.

> Operational internals (schedules, query lists, maintenance scripts, resume steps) live in **[SYSTEM_GUIDE.md](SYSTEM_GUIDE.md)**. This README explains what the platform does and how to use it.

---

## What it does

- **Finds reviews automatically.** Hundreds of targeted YouTube searches (named systems like "Panasonic Astrova", airline × aircraft combinations, generic IFE phrasings) run on a daily schedule — in the cloud via GitHub Actions and locally while the app runs. Press articles come from a curated source list.
- **Reads them.** Every video gets its metadata (channel, date, views, likes), and where possible a transcript — YouTube captions first, local Whisper speech-to-text as fallback. Non-English titles, captions, and comments are auto-translated to English with the original preserved.
- **Tags them.** Each review is matched against keyword taxonomies for airlines, aircraft types, named IFE systems, and ~90 IFE feature keywords. A system tag is applied **only when the system is explicitly named** in the content — no guessing. Uncertain matches are stored as hidden hints, and tags can be corrected by hand.
- **Aggregates everything** into dashboards: popularity, trends by year, momentum, regional splits, feature coverage per system, reviewer-channel reach, and viewer comments that mention IFE hardware.
- **Lets the team work on it together:** shared notes on any video, shared saved-videos list, filtered CSV exports, a printable intelligence digest, and an AI chat that answers questions grounded in the review corpus.

## How it works

```
YouTube Data API + article sources
        │  (daily cloud crawl via GitHub Actions + local crawl + Crawl button)
        ▼
ife_crawler.py  ──  discovery, metadata, transcripts, keyword tagging
        ▼
ife_cache.json  ──  the database (committed to git; CI and local runs sync through it)
        ▼
app.py (Flask)  ──  APIs, aggregates, notes/bookmarks, manual tag edits
        ▼
templates/index.html  ──  the dashboard (single page, five tabs)
```

- The **database is a JSON file in the repo**. Cloning the repo gives you the full dataset — no crawling needed to start.
- The **cloud crawl commits daily** (3 AM UTC). Local work (transcript backfills, manual tags) is committed and pushed from the host machine. `git pull` before working, `git push` after — dedupe-by-URL resolves overlaps.
- Everything user-generated lives server-side next to the app: `notes.json` (team notes), `flags.json` (saved videos), manual tag corrections inside the cache.

## Getting started

```bash
git clone https://github.com/eviesraveaerospace/ifereviewdatabase.git
cd ifereviewdatabase
pip install -r requirements.txt
python serve.py
```

`serve.py` binds to all interfaces and prints a share link (`http://<your-ip>:5000/`) others on the same network can open. Use `python app.py` instead for a localhost-only instance.

Optional `.env` keys:

| Key | Enables |
|---|---|
| `YOUTUBE_API_KEY` | Crawling for new reviews (dashboard works without it on existing data) |
| `ANTHROPIC_API_KEY` | The Ask AI tab |

## Navigating the dashboard

### Dashboard (home)

- **Videos / Articles tiles** — library counts; click one to open the Reviews tab pre-filtered to that type.
- **Popular YouTube channels** — reviewer channels that have IFE reviews in the library, with subscriber counts. Click a channel to see its reviews; **View All** opens channel statistics.
- **New videos** — every video published in a chosen window (last 7/14/30/90/180/365 days), newest first, scrollable. Built for periodic check-ins: pick "Last 30 days" and scroll everything new since last time.
- **Popular Features** — bar chart of the most-discussed IFE features. **Click a bar** for that feature's breakdown: reviews/views/likes/transcript mentions, which systems and airlines it appears with, a yearly trend, and its videos ranked by popularity. "All Features" opens Statistics.
- **Comments** — real viewer/creator comments that mention IFE hardware; click one to jump to that video at the quoted moment.
- **Top bar (all tabs):** Crawl button (triggers a background discovery crawl), report icon (printable intelligence digest), share icon (copies a shareable link including your current filters), bookmark icon (your team's saved videos).

### Reviews

The library browser. Newest first by default.

- **Search** covers titles, transcripts, chapters, and team notes.
- **Facet filters:** Airline, System, Feature, Type, Year, Source, Transcript, Chapters. Active filters show as removable pills; leaving the tab resets them.
- **Export CSV** downloads exactly what the current filters show.
- **Click a video** to open the in-app player modal:
  - chapters (IFE-relevant ones flagged ✦) and **transcript "IFE moments"** — click any line to jump the player to that timestamp;
  - **Notes** — shared with the whole team, searchable;
  - **Bookmark** — adds to the shared saved-videos list;
  - **✎ system tag editor** — set or clear the review's IFE system by hand. Only visible and only accepted from the machine hosting the server; manual tags are protected from automation.
- Articles open directly in a new tab.

### Statistics

KPIs, review volume by year, what's rising (momentum), reviews by region, reach by system, most-discussed features, review coverage gaps, reviewer channels, systems and airlines tables. **Nearly every row and bar is clickable** and drills into the Reviews tab pre-filtered (feature bars open the feature breakdown instead). Note the coverage-gaps panel tracks what *reviewers* have covered — a feature listed as missing means no review mentions it, not that the system lacks it.

### Compare

Pick two IFE systems (A vs B): reach, engagement, momentum, airline overlap, and a feature-by-feature coverage matrix.

### Ask AI

Ask questions in plain language ("Which airlines have Starlink?", "What is RAVE up to lately?"). Answers are generated from the review corpus and cite the videos used. Requires `ANTHROPIC_API_KEY` on the host.

## Data quality rules worth knowing

- **System tags are conservative.** Only explicitly-named systems are tagged (~10% of reviews); everything else stays untagged rather than guessed. Use the ✎ editor to confirm systems video-by-video.
- **Transcript coverage is ongoing.** Videos without captions get Whisper-transcribed in batches (`backfill_transcripts.py`); coverage grows over time.
- **Translations preserve originals.** English text is shown; the source text and language stay attached underneath.

## Contributing

- `git pull` before you start — the cloud crawler commits daily.
- Code changes: edit, commit, push (or fork + PR). The whole UI is one file, [templates/index.html](templates/index.html); the API is [app.py](app.py).
- Data corrections happen in the dashboard (notes, tags), not by editing `ife_cache.json` by hand.
- See [SYSTEM_GUIDE.md](SYSTEM_GUIDE.md) for schedules, query/keyword inventories, maintenance scripts, and how to resume in-flight work.
