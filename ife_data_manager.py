import json
import os
from datetime import datetime
from ife_crawler import IFECrawler


class IFEDataManager:
    """Manages cached IFE review data with filtering and pagination."""

    def __init__(self, cache_file="ife_cache.json"):
        self.cache_file = cache_file
        self.data = self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"reviews": [], "last_updated": None}

    def save_cache(self):
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def reload_from_disk(self):
        """Re-read cache from disk (called before every API response)."""
        self.data = self.load_cache()
        self._backfill_fields()
        # Exclude Tier 3 sources — only known press (T1) and creators (T2)
        self.data["reviews"] = [
            r for r in self.data.get("reviews", [])
            if r.get("source_tier", 3) < 3
        ]

    def _backfill_fields(self):
        """Add default values for fields introduced after initial seed."""
        from ife_crawler import infer_ife_system, source_tier as compute_tier
        for r in self.data.get("reviews", []):
            r.setdefault("ife_specs", {})
            r.setdefault("ife_system_inferred", False)
            # Recompute tier from URL so seeded records get the right value
            if "source_tier" not in r or r.get("source_name") == "General":
                if r.get("media_type") == "video":
                    r["source_tier"] = 2
                    r["source_name"] = "YouTube"
                else:
                    t = compute_tier(r.get("url", ""))
                    r["source_tier"] = t
                    r["source_name"] = {1: "Press", 2: "Creator"}.get(t, "General")
            # Backfill start_seconds on captions that only have a "M:SS" string
            for cap in r.get("captions", []):
                if "start_seconds" not in cap and cap.get("timestamp"):
                    try:
                        parts = cap["timestamp"].split(":")
                        cap["start_seconds"] = int(parts[0]) * 60 + int(parts[1])
                    except Exception:
                        pass
            # Backfill inference for seeded records with no detected system
            if not r.get("ife_system"):
                inferred = infer_ife_system(
                    r.get("airlines_mentioned", []),
                    r.get("aircraft_mentioned", [])
                )
                if inferred:
                    r["ife_system"] = inferred
                    r["ife_system_inferred"] = True

    def crawl_and_cache(self, airline=None, aircraft=None):
        crawler = IFECrawler(verify_ssl=False)
        results = crawler.crawl_review_sites(airline=airline, aircraft=aircraft)
        self.data["reviews"].extend(results)
        self.save_cache()
        return results

    def get_filter_options(self):
        """Return all distinct values for each filterable field."""
        airlines = set()
        aircraft = set()
        ife_systems = set()
        ife_features = set()
        years = set()
        media_types = set()
        transcript_options = {"Yes", "No"}

        for r in self.data.get("reviews", []):
            for a in r.get("airlines_mentioned", []):
                airlines.add(a["keyword"])
            for ac in r.get("aircraft_mentioned", []):
                aircraft.add(ac["keyword"])
            if r.get("ife_system"):
                ife_systems.add(r["ife_system"])
            for f in r.get("ife_features", {}).keys():
                ife_features.add(f)
            if r.get("year"):
                years.add(r["year"])
            if r.get("media_type"):
                media_types.add(r["media_type"])

        source_tiers = {"Press (T1)", "Creator (T2)", "General (T3)"}

        return {
            "years":        sorted(years, reverse=True),
            "airlines":     sorted(airlines),
            "ife_systems":  sorted(ife_systems),
            "ife_features": sorted(ife_features),
            "media_types":  sorted(media_types),
            "transcript":   sorted(transcript_options),
            "source_tiers": sorted(source_tiers),
        }

    def _relevance(self, r):
        """Compute an IFE content density score (purely factual, not quality)."""
        score = 0.0
        score += min(len(r.get("ife_features", {})) * 0.15, 0.6)
        if r.get("ife_system"):
            score += 0.2
        if r.get("transcript_available"):
            score += 0.15
        score += min(len(r.get("airlines_mentioned", [])) * 0.05, 0.15)
        return round(min(score, 1.0), 3)

    def filter_reviews(self, filters):
        results = self.data.get("reviews", [])

        if filters.get("airlines"):
            results = [r for r in results if any(
                a["keyword"] in filters["airlines"]
                for a in r.get("airlines_mentioned", [])
            )]

        if filters.get("aircraft"):
            results = [r for r in results if any(
                ac["keyword"] in filters["aircraft"]
                for ac in r.get("aircraft_mentioned", [])
            )]

        if filters.get("ife_systems"):
            results = [r for r in results if r.get("ife_system") in filters["ife_systems"]]

        if filters.get("ife_features"):
            results = [r for r in results if any(
                f in r.get("ife_features", {})
                for f in filters["ife_features"]
            )]

        if filters.get("years"):
            results = [r for r in results if r.get("year") in filters["years"]]

        if filters.get("media_types"):
            results = [r for r in results if r.get("media_type") in filters["media_types"]]

        if filters.get("transcript"):
            want = filters["transcript"]
            if "Yes" in want and "No" not in want:
                results = [r for r in results if r.get("transcript_available")]
            elif "No" in want and "Yes" not in want:
                results = [r for r in results if not r.get("transcript_available")]

        if filters.get("source_tiers"):
            tier_map = {"Press (T1)": 1, "Creator (T2)": 2, "General (T3)": 3}
            wanted = {tier_map[t] for t in filters["source_tiers"] if t in tier_map}
            if wanted:
                results = [r for r in results if r.get("source_tier", 3) in wanted]

        # Always sort by relevance descending
        results.sort(key=self._relevance, reverse=True)
        return results

    def paginate(self, rows, page, per_page=50):
        total = len(rows)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        return {
            "rows": rows[start:start + per_page],
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        }

    def get_summary(self, reviews=None):
        reviews = reviews if reviews is not None else self.data.get("reviews", [])
        if not reviews:
            return {}

        airlines = {}
        aircraft = {}
        ife_systems = {}
        features = {}
        media_types = {}
        with_transcript = 0

        for r in reviews:
            for a in r.get("airlines_mentioned", []):
                airlines[a["keyword"]] = airlines.get(a["keyword"], 0) + a["mentions"]
            for ac in r.get("aircraft_mentioned", []):
                aircraft[ac["keyword"]] = aircraft.get(ac["keyword"], 0) + ac["mentions"]
            sys = r.get("ife_system", "Unknown")
            ife_systems[sys] = ife_systems.get(sys, 0) + 1
            for f in r.get("ife_features", {}).keys():
                features[f] = features.get(f, 0) + 1
            mt = r.get("media_type", "unknown")
            media_types[mt] = media_types.get(mt, 0) + 1
            if r.get("transcript_available"):
                with_transcript += 1

        return {
            "total_reviews":    len(reviews),
            "with_transcript":  with_transcript,
            "top_airlines":     sorted(airlines.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_aircraft":     sorted(aircraft.items(), key=lambda x: x[1], reverse=True)[:5],
            "ife_systems":      sorted(ife_systems.items(), key=lambda x: x[1], reverse=True),
            "ife_features":     sorted(features.items(), key=lambda x: x[1], reverse=True),
            "media_types":      media_types,
        }

    def clear_cache(self):
        self.data = {"reviews": [], "last_updated": None}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
