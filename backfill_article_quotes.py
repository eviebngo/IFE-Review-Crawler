"""One-off: re-fetch cached press articles and extract 'strong quotes'
(top IFE-relevant sentences with matched keywords) into article_quotes,
for the article popup modal. Articles that no longer load are skipped.

Run:  python backfill_article_quotes.py
"""
import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

from ife_crawler import _article_quotes

CACHE = Path(__file__).parent / "ife_cache.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

data = json.loads(CACHE.read_text(encoding="utf-8"))
articles = [r for r in data.get("reviews", [])
            if r.get("media_type") == "article" and not r.get("article_quotes")]
print(f"Articles without quotes: {len(articles)}")

done = fail = 0
for r in articles:
    url = r.get("url", "")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        quotes = _article_quotes(soup.get_text(separator=" "))
        r["article_quotes"] = quotes
        done += 1
        print(f"  OK   {len(quotes)} quotes  {url[:80]}")
    except Exception as e:
        fail += 1
        print(f"  FAIL {type(e).__name__}: {str(e)[:60]}  {url[:80]}")

CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nDone: {done} updated, {fail} failed. Saved {CACHE.name}.")
