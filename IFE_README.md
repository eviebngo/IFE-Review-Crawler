# IFE (In-Flight Entertainment) Crawler

A specialized web crawler designed to search airline reviews and extract in-flight entertainment (IFE) product information.

## Features

### 1. General Web Crawler
- Crawl any website with configurable depth and page limits
- Extract metadata, tags, year, and transcript information
- Save results in JSON format

**Endpoint:** `POST /api/crawl`

### 2. IFE Review Search
- Search for airline reviews with focus on IFE systems
- Filter by airline and/or aircraft type
- Extracts:
  - IFE relevance score (0-1)
  - Airlines mentioned
  - Aircraft mentioned
  - IFE features found
  - Sentiment analysis (positive/negative/neutral)

**Endpoint:** `POST /api/search-ife`

**Example:**
```bash
curl -X POST http://127.0.0.1:5000/api/search-ife \
  -H "Content-Type: application/json" \
  -d '{"airline": "United", "aircraft": "787", "max_results": 20}'
```

### 3. Review Sites Crawler
- Crawl major airline review sites automatically
- Targets: TripAdvisor, SeatGuru, SkyTrax, etc.
- Aggregates IFE information across sites

**Endpoint:** `POST /api/crawl-review-sites`

**Example:**
```bash
curl -X POST http://127.0.0.1:5000/api/crawl-review-sites \
  -H "Content-Type: application/json" \
  -d '{"airline": "Emirates", "aircraft": "A350"}'
```

## IFE Keywords Tracked

### Entertainment System
- entertainment system, IFE, in-flight entertainment, seatback screen, personal screen, video on demand, VOD

### Content
- movies, TV shows, music, games, podcasts, audiobooks, audio

### Seat Features
- seat, recline, legroom, comfort, cushion, armrest, headrest

### Connectivity
- WiFi, internet, connectivity, Bluetooth, in-flight connectivity

### Quality Indicators
- quality, resolution, lag, refresh rate, display, screen, picture

### Airlines & Aircraft
- United, American, Delta, Southwest, Emirates, Lufthansa, etc.
- 787, 777, A350, A380, Airbus, Boeing

## Results Format

Each result includes:
- `url` - Source URL
- `title` - Review title/source
- `ife_relevance_score` - 0-1 score indicating how relevant to IFE (higher = more relevant)
- `airlines_mentioned` - List of airlines found with mention counts
- `aircraft_mentioned` - List of aircraft found with mention counts
- `ife_features` - Dictionary of detected IFE features
- `sentiment` - positive/negative/neutral analysis

## Summary Statistics

Each search returns aggregated data:
- `total_reviews_analyzed` - Number of reviews processed
- `top_airlines` - Most frequently mentioned airlines
- `top_aircraft` - Most frequently mentioned aircraft
- `ife_features_frequency` - How often each IFE feature appears
- `average_relevance` - Average IFE relevance across results

## Usage

### Start the server:
```bash
py -3 app.py
```

### Access the web app:
Open `http://127.0.0.1:5000` in your browser

### Via API:

**Search for IFE reviews:**
```bash
curl -X POST http://127.0.0.1:5000/api/search-ife \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "United",
    "aircraft": "787",
    "max_results": 20
  }'
```

**Crawl review sites:**
```bash
curl -X POST http://127.0.0.1:5000/api/crawl-review-sites \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "Emirates",
    "aircraft": "A350"
  }'
```

## Output Files

- `ife_results.json` - Latest IFE search results
- `results.json` - Latest general crawler results

## Key Metrics

The crawler provides:
1. **Relevance Score** - How focused a review is on IFE (0-1)
2. **Sentiment** - Positive/negative sentiment about IFE
3. **Feature Detection** - Which IFE aspects are mentioned
4. **Cross-platform Analysis** - Aggregates across multiple review sites

## Example: Finding 787 IFE Reviews

```bash
curl -X POST http://127.0.0.1:5000/api/search-ife \
  -H "Content-Type: application/json" \
  -d '{
    "aircraft": "787",
    "max_results": 50
  }' | python -m json.tool
```

This will return all reviews mentioning 787 in-flight entertainment systems with:
- Relevance scores for filtering
- Which airlines use them
- What entertainment content is available
- Overall sentiment about their quality
