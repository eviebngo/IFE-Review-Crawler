import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass
from ife_crawler import IFECrawler
from ife_data_manager import IFEDataManager

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

data_manager = IFEDataManager()
PER_PAGE = 50

# ── Background auto-discovery ─────────────────────────────────────────────────

# Interval between discovery runs (seconds). First run is immediate.
CRAWL_INTERVAL = 86400  # re-crawl once per day

_crawl_status = {
    "running":      False,
    "last_run":     None,
    "last_added":   0,
    "next_run":     None,
    "error":        None,
}


def _run_auto_discovery():
    """Background thread: search for IFE reviews by keyword and cache new ones."""
    global _crawl_status
    while True:
        _crawl_status["running"] = True
        _crawl_status["error"] = None
        try:
            data_manager.reload_from_disk()
            existing = {r["url"] for r in data_manager.data.get("reviews", [])}

            crawler = IFECrawler(verify_ssl=False, api_key=os.environ.get("YOUTUBE_API_KEY", ""))
            new_results = crawler.auto_discover(existing_urls=existing, max_results=500, days_lookback=7)

            if new_results:
                data_manager.data["reviews"].extend(new_results)
                data_manager.save_cache()

            _crawl_status["last_added"] = len(new_results)
            _crawl_status["last_run"] = datetime.now().isoformat()
        except Exception as e:
            _crawl_status["error"] = str(e)
        finally:
            _crawl_status["running"] = False
            _crawl_status["next_run"] = datetime.fromtimestamp(
                time.time() + CRAWL_INTERVAL
            ).isoformat()

        time.sleep(CRAWL_INTERVAL)


def start_background_crawler():
    t = threading.Thread(target=_run_auto_discovery, daemon=True)
    t.start()


def _purge_tier3_articles():
    """One-time startup: remove Tier 3 articles from the JSON cache file."""
    data_manager.reload_from_disk()
    before = len(data_manager.load_cache().get("reviews", []))
    kept   = len(data_manager.data.get("reviews", []))
    if kept < before:
        data_manager.save_cache()


def _initial_seed():
    """If the database is small, do a one-time broad crawl before the daily loop starts."""
    data_manager.reload_from_disk()
    if len(data_manager.data.get("reviews", [])) < 50:
        try:
            existing = {r["url"] for r in data_manager.data.get("reviews", [])}
            crawler  = IFECrawler(verify_ssl=False, api_key=os.environ.get("YOUTUBE_API_KEY", ""))
            results  = crawler.auto_discover(existing_urls=existing, max_results=500, days_lookback=365)
            if results:
                data_manager.reload_from_disk()
                data_manager.data["reviews"].extend(results)
                data_manager.save_cache()
        except Exception as e:
            print(f"[seed] error: {e}")


# Start on import (Flask dev-mode forks; only start once via the werkzeug check)
if not os.environ.get("WERKZEUG_RUN_MAIN") == "false":
    _purge_tier3_articles()
    threading.Thread(target=_initial_seed, daemon=True).start()
    start_background_crawler()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ife-reviews")
def get_ife_reviews():
    """Paginated full review list."""
    try:
        page = int(request.args.get("page", 1))
        data_manager.reload_from_disk()
        reviews = sorted(
            data_manager.data.get("reviews", []),
            key=data_manager._relevance,
            reverse=True
        )
        paged = data_manager.paginate(reviews, page, PER_PAGE)
        return jsonify({
            "status": "success",
            "last_updated": data_manager.data.get("last_updated"),
            "summary": data_manager.get_summary(reviews),
            **paged,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ife-filter-options")
def get_filter_options():
    try:
        data_manager.reload_from_disk()
        return jsonify({
            "status": "success",
            "options": data_manager.get_filter_options()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ife-filter", methods=["POST"])
def filter_ife_reviews():
    """Filter + paginate reviews. Accepts optional _search for title text search."""
    try:
        body = request.get_json() or {}
        page   = int(body.pop("page", 1))
        search = body.pop("_search", "").strip().lower()

        data_manager.reload_from_disk()
        filtered = data_manager.filter_reviews(body)

        if search:
            def _matches(r):
                if search in (r.get("title") or "").lower():
                    return True
                if search in (r.get("transcript_excerpt") or "").lower():
                    return True
                if any(search in (c.get("text") or "").lower() for c in r.get("captions") or []):
                    return True
                return False
            filtered = [r for r in filtered if _matches(r)]

        paged = data_manager.paginate(filtered, page, PER_PAGE)
        return jsonify({
            "status": "success",
            "last_updated": data_manager.data.get("last_updated"),
            "summary": data_manager.get_summary(filtered),
            **paged,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ife-seed", methods=["POST"])
def ife_seed():
    """Manually trigger a 100-result discovery crawl in the background."""
    def _run():
        try:
            data_manager.reload_from_disk()
            existing = {r["url"] for r in data_manager.data.get("reviews", [])}
            crawler  = IFECrawler(verify_ssl=False, api_key=os.environ.get("YOUTUBE_API_KEY", ""))
            results  = crawler.auto_discover(existing_urls=existing, max_results=500, days_lookback=365)
            if results:
                data_manager.reload_from_disk()
                data_manager.data["reviews"].extend(results)
                data_manager.save_cache()
        except Exception as e:
            print(f"[manual-seed] {e}")
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "success", "message": "seed crawl started in background"})


@app.route("/api/ife-refresh")
def ife_refresh():
    """Lightweight poll: last_updated + total count + crawl status."""
    try:
        data_manager.reload_from_disk()
        return jsonify({
            "status":       "success",
            "last_updated": data_manager.data.get("last_updated"),
            "total":        len(data_manager.data.get("reviews", [])),
            "crawl":        _crawl_status,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
