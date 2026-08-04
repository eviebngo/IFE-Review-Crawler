"""Generate the analyzed sample report requested by the YouTube API Services
compliance review: what data the API client collects, how videos are matched
to airlines/IFE systems/features, and how transcripts are analyzed — all
illustrated with real records from the database.

Run:   python generate_compliance_report.py
Out:   compliance_sample_report.html  (open in a browser, print to PDF)
"""
import json
from datetime import date
from html import escape

from ife_crawler import IFE_FEATURE_KEYWORDS

FEAT_LABELS = {
    "entertainment_system": "IFE System", "connectivity": "In-flight WiFi",
    "4k_display": "4K HDR Display", "bluetooth_audio": "Bluetooth Audio",
    "content": "Content Library", "quality": "Display Quality",
    "seat": "Seat Comfort", "usb_power": "USB Power", "watch_party": "Watch Party",
    "seat_chat": "Seat-to-Seat Chat", "search": "Content Search",
    "tail_camera": "Tail / External Camera", "moving_map": "Moving Map",
}

data = json.load(open("ife_cache.json", encoding="utf-8"))
reviews = [r for r in data.get("reviews", []) if r.get("media_type") == "video"]

total = len(reviews)
with_tx = sum(1 for r in reviews if r.get("transcript_available"))
tagged = sum(1 for r in reviews if r.get("ife_system"))

# ── pick 5 rich sample records (transcript + system + airline + features) ──
rich = [r for r in reviews
        if r.get("transcript_available") and r.get("ife_system")
        and r.get("airlines_mentioned") and r.get("ife_features")]
rich.sort(key=lambda r: int(r.get("view_count") or 0), reverse=True)
samples = rich[:5]

# ── caption lines that matched feature keywords (transcription analysis) ──
def matched_caps(r, limit=3):
    out = []
    for c in r.get("captions", []):
        t = (c.get("text") or "").lower()
        for key, kws in IFE_FEATURE_KEYWORDS.items():
            hit = next((kw for kw in kws if kw in t), None)
            if hit:
                out.append((c.get("timestamp", ""), c.get("text", ""), FEAT_LABELS.get(key, key), hit))
                break
        if len(out) >= limit:
            break
    return out

# ── aggregates (the internal analysis outputs) ──
feat_counts, sys_counts, year_counts = {}, {}, {}
for r in reviews:
    for f in (r.get("ife_features") or {}):
        feat_counts[f] = feat_counts.get(f, 0) + 1
    if r.get("ife_system"):
        sys_counts[r["ife_system"]] = sys_counts.get(r["ife_system"], 0) + 1
    if r.get("year"):
        year_counts[r["year"]] = year_counts.get(r["year"], 0) + 1

def vid_id(u):
    return u.split("v=")[-1].split("&")[0] if "v=" in (u or "") else (u or "").rsplit("/", 1)[-1]

def row(cells, tag="td"):
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"

sample_rows = ""
for r in samples:
    feats = ", ".join(FEAT_LABELS.get(f, f) for f in (r.get("ife_features") or {}))
    airs = ", ".join(a["keyword"].title() for a in r.get("airlines_mentioned", [])[:3])
    sample_rows += row([
        f"<code>{escape(vid_id(r['url']))}</code>", escape(r.get("title", "")[:80]),
        escape(r.get("channel_title", "")), escape(str(r.get("published_at", ""))[:10]),
        f"{int(r.get('view_count') or 0):,}", escape(airs),
        escape(r.get("ife_system") or "—"), escape(feats),
    ])

cap_blocks = ""
for r in samples[:3]:
    caps = matched_caps(r)
    if not caps:
        continue
    cap_blocks += f"<h4>{escape(r.get('title','')[:90])} <span class='muted'>(video {escape(vid_id(r['url']))})</span></h4><table>"
    cap_blocks += row(["Timestamp", "Caption line (as spoken)", "Matched feature", "Matched keyword"], "th")
    for ts, text, label, kw in caps:
        cap_blocks += row([escape(ts), escape(text[:140]), escape(label), f"<code>{escape(kw)}</code>"])
    cap_blocks += "</table>"

feat_rows = "".join(row([escape(FEAT_LABELS.get(k, k)), f"{c:,}", f"{c/total*100:.0f}%"])
                    for k, c in sorted(feat_counts.items(), key=lambda x: -x[1])[:8])
sys_rows = "".join(row([escape(k), f"{c:,}"]) for k, c in sorted(sys_counts.items(), key=lambda x: -x[1])[:8])
year_rows = "".join(row([y, f"{c:,}"]) for y, c in sorted(year_counts.items()))

html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>YouTube API Client — Analyzed Sample Report</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;color:#111;max-width:900px;margin:32px auto;line-height:1.5;font-size:13px}}
h1{{font-size:22px;margin-bottom:2px}} h2{{font-size:16px;margin-top:28px;border-bottom:2px solid #111;padding-bottom:4px}}
h4{{margin:16px 0 6px}} .muted{{color:#777;font-weight:400}}
table{{border-collapse:collapse;width:100%;margin:8px 0}} th,td{{border:1px solid #ccc;padding:5px 8px;text-align:left;vertical-align:top}}
th{{background:#f2f2f2;font-size:11px;text-transform:uppercase}} code{{background:#f5f5f5;padding:1px 4px}}
.kpis{{display:flex;gap:24px;margin:14px 0}} .kpi b{{display:block;font-size:20px}}
@media print{{body{{margin:10mm}}}}
</style></head><body>
<h1>Analyzed Sample Report — YouTube Collected Data</h1>
<p class="muted">IFE Review Database (internal competitive-intelligence dashboard) · Prepared {date.today():%B %d, %Y} · Contact: evie.ngo@zii.aero</p>

<h2>1. Purpose and use of YouTube API data</h2>
<p>The API client discovers <b>public YouTube videos reviewing airline in-flight entertainment (IFE) systems</b>
using YouTube Data API v3 (<code>search.list</code>, <code>videos.list</code>, <code>commentThreads.list</code>).
Collected metadata is analyzed <b>internally only</b> to monitor how IFE systems and features are discussed by
independent reviewers. The analysis dashboard is available to our internal team on our office network;
data is not sold, published, or redistributed. Videos are always presented via the official YouTube embedded
player with attribution and links back to YouTube.</p>
<div class="kpis"><div class="kpi"><b>{total:,}</b>videos indexed</div>
<div class="kpi"><b>{with_tx:,}</b>with caption analysis</div>
<div class="kpi"><b>{tagged:,}</b>matched to a named IFE system</div></div>

<h2>2. Data collected per video (API fields)</h2>
<table>{row(['API field','Example use in analysis'],'th')}
{row(['<code>id.videoId</code> / URL','Unique key; deduplication; embedded playback link'])}
{row(['<code>snippet.title</code>','Airline / aircraft / IFE-system keyword matching'])}
{row(['<code>snippet.channelTitle</code>','Reviewer channel attribution and per-channel statistics'])}
{row(['<code>snippet.publishedAt</code>','Review-volume trend by year'])}
{row(['<code>statistics.viewCount</code>, <code>likeCount</code>','Reach and engagement weighting of findings'])}
{row(['<code>commentThreads.list</code> text (public comments)','Surfacing viewer feedback that references IFE hardware/features'])}</table>

<h2>3. Matching analysis — sample records</h2>
<p>Each video's title and transcript text are matched against curated keyword taxonomies
(airlines, aircraft, named IFE systems such as "Panasonic eX3" or "Safran RAVE", and feature vocabularies).
A system is tagged only when explicitly named in the content. Sample of {len(samples)} real records:</p>
<table>{row(['Video ID','Title','Channel','Published','Views','Matched airlines','Matched IFE system','Matched features'],'th')}{sample_rows}</table>

<h2>4. Transcription analysis — sample matched caption lines</h2>
<p>Publicly available caption tracks are scanned for feature vocabulary; matching lines (with timestamps)
let analysts jump to the exact moment a feature is discussed in the embedded player.</p>
{cap_blocks}

<h2>5. Aggregated internal analysis outputs</h2>
<table style="width:48%;display:inline-table;margin-right:2%">{row(['Feature discussed','Videos','Share'],'th')}{feat_rows}</table>
<table style="width:48%;display:inline-table">{row(['Named IFE system','Videos'],'th')}{sys_rows}</table>
<table style="width:48%">{row(['Year published','Videos'],'th')}{year_rows}</table>

<h2>6. Data handling</h2>
<p>Metadata is stored in a private project datastore and refreshed by a scheduled daily crawl within quota.
Videos found to be private or removed are purged from the datastore. Access is restricted to the internal
project team. Full policies: see the project's published Privacy Policy and Terms of Service.</p>
</body></html>"""

open("compliance_sample_report.html", "w", encoding="utf-8").write(html)
print(f"written compliance_sample_report.html — {total:,} videos, {with_tx:,} with transcripts, {len(samples)} sample records")
