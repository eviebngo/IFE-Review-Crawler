import json

with open("ife_cache_local.json", encoding="utf-8") as f:
    local = json.load(f)
with open("ife_cache.json", encoding="utf-8") as f:
    remote = json.load(f)

local_with_transcripts = {
    r["url"]: r for r in local.get("reviews", [])
    if r.get("transcript_available") and r.get("transcript_excerpt")
}

applied = 0
for r in remote.get("reviews", []):
    url = r.get("url", "")
    if url in local_with_transcripts:
        src = local_with_transcripts[url]
        r["transcript_available"] = True
        r["transcript_excerpt"] = src.get("transcript_excerpt", "")
        r["captions"] = src.get("captions", [])
        if src.get("transcript_source"):
            r["transcript_source"] = src["transcript_source"]
        applied += 1

with open("ife_cache.json", "w", encoding="utf-8") as f:
    json.dump(remote, f, indent=2, ensure_ascii=False)

total = len(remote["reviews"])
print(f"Applied {applied} Whisper transcripts onto remote cache ({total} total videos)")
