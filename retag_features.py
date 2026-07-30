"""One-off: re-tag ife_features on every cached review using the current
IFE_FEATURE_KEYWORDS (adds newly-detected features like watch_party,
seat_chat, search, tail_camera, moving_map; never removes existing tags,
since some originals were tagged from video descriptions we don't store).

Run:  python retag_features.py
"""
from ife_crawler import IFE_FEATURE_KEYWORDS
from ife_data_manager import IFEDataManager

dm = IFEDataManager()
dm.reload_from_disk()
reviews = dm.data.get("reviews", [])

changed = 0
added = {}
for r in reviews:
    parts = [r.get("title") or "", r.get("transcript_excerpt") or "",
             r.get("transcript_full") or ""]
    parts += [c.get("text", "") for c in (r.get("captions") or [])]
    parts += [c.get("title", "") for c in (r.get("chapters") or [])]
    text = " ".join(parts).lower()

    feats = dict(r.get("ife_features") or {})
    before = set(feats)
    for f, kws in IFE_FEATURE_KEYWORDS.items():
        if f not in feats and any(kw in text for kw in kws):
            feats[f] = True
    new = set(feats) - before
    if new:
        r["ife_features"] = feats
        changed += 1
        for f in new:
            added[f] = added.get(f, 0) + 1

if changed:
    dm.save_cache()
print(f"reviews scanned: {len(reviews)}, updated: {changed}")
for f, c in sorted(added.items(), key=lambda x: -x[1]):
    print(f"  +{c:4d}  {f}")
