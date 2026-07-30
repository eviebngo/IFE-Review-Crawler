# ifereviewdatabase

This is my Summer 2026 IFE Review Database project! Feel free to clone this repo and make edits on your own. Happy researching!

A dashboard + crawler that collects public YouTube reviews of in-flight entertainment (IFE) systems and turns them into searchable, filterable competitive intelligence: which systems airlines run, which features reviewers talk about (4K, Bluetooth audio, moving map, tail camera, watch party…), and how coverage trends over time.

## Quickstart

```bash
pip install -r requirements.txt
python serve.py          # dashboard on http://<your-ip>:5000 (LAN-shareable)
# or: python app.py      # localhost only
```

Set `YOUTUBE_API_KEY` in a `.env` file to enable crawling.

## What's here

| File | Purpose |
|---|---|
| `app.py` | Flask backend — API, aggregates, notes, manual tag editing |
| `serve.py` | LAN launcher (binds 0.0.0.0, prints share links) |
| `ife_crawler.py` | YouTube discovery crawl + airline/system/feature tagging |
| `ife_data_manager.py` | Cache load/save, filtering, pagination |
| `ife_cache.json` | The review database (also updated daily by CI) |
| `templates/index.html` | The whole dashboard UI |
| `backfill_transcripts.py` | Fetch transcripts for cached videos (captions → Whisper fallback) |
| `gather_*.py`, `regather_captions.py`, `translate_captions.py` | Enrichment scripts (channels, chapters, comments) |
| `.github/workflows/` | Daily cloud crawl + transcript backfill (need `YOUTUBE_API_KEY` / `YOUTUBE_COOKIES_B64` secrets) |

## Notes for contributors

- `git pull` before pushing — CI commits a daily cache update to `main`.
- Manual IFE-system tag edits in the UI are restricted to the machine hosting the server.
- Only explicitly-detected IFE systems get tagged; airline-based inferences are stored as hidden guesses.
