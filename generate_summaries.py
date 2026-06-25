"""
Generate AI summaries for IFE cache entries that don't have one yet.
Uses claude-haiku-4-5-20251001 for speed and low cost (~$0.001 per entry).

Usage:
  python generate_summaries.py            # process all missing summaries
  python generate_summaries.py --limit 50 # process only N entries
"""
import json
import os
import sys
import time
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)


SYSTEM_PROMPT = (
    "You are a concise analyst summarizing in-flight entertainment (IFE) reviews "
    "for airline industry professionals. Focus on what system is reviewed, the "
    "reviewer's impression of content/screen quality, and any notable pros or cons. "
    "Never speculate beyond what the source states. Write in third person, present tense."
)


def build_context(r: dict) -> str:
    parts = [f"Title: {r.get('title', 'Unknown')[:120]}"]
    if r.get("ife_system"):
        parts.append(f"IFE System: {r['ife_system']}")
    airlines = [a["keyword"].title() for a in r.get("airlines_mentioned", [])[:2]]
    if airlines:
        parts.append(f"Airline(s): {', '.join(airlines)}")
    aircraft = [a["keyword"].upper() for a in r.get("aircraft_mentioned", [])[:2]]
    if aircraft:
        parts.append(f"Aircraft: {', '.join(aircraft)}")
    features = list(r.get("ife_features", {}).keys())
    if features:
        parts.append(f"Detected features: {', '.join(features)}")
    if r.get("transcript_excerpt"):
        parts.append(f"Review excerpt: {r['transcript_excerpt'][:350]}")
    caps = r.get("captions", [])[:3]
    if caps:
        cap_text = " | ".join(c["text"] for c in caps if c.get("text"))
        if cap_text:
            parts.append(f"Quotes: {cap_text[:450]}")
    return "\n".join(parts)


def summarize(client: anthropic.Anthropic, r: dict) -> str:
    context = build_context(r)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=120,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                "Summarize this IFE review in exactly 2 sentences. "
                "Sentence 1: what system/airline is covered and one key impression. "
                "Sentence 2: a specific detail about content, screen quality, or connectivity.\n\n"
                + context
            ),
        }],
    )
    return msg.content[0].text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max entries to process (0 = all)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to .env or set as environment variable.")
        sys.exit(1)

    with open("ife_cache.json", encoding="utf-8") as f:
        data = json.load(f)

    reviews = data.get("reviews", [])
    targets = [r for r in reviews if not r.get("ai_summary")]
    if args.limit:
        targets = targets[: args.limit]

    print(f"Entries without AI summary: {len(targets)}")
    if not targets:
        print("Nothing to do.")
        return

    client = anthropic.Anthropic(api_key=api_key)
    done = failed = 0

    for idx, r in enumerate(targets, 1):
        try:
            summary = summarize(client, r)
            r["ai_summary"] = summary
            done += 1
            print(f"[{idx}/{len(targets)}] OK   {r.get('title', '')[:55]}")
        except Exception as e:
            failed += 1
            print(f"[{idx}/{len(targets)}] FAIL {r.get('title', '')[:55]} — {e}")

        # Save every 20 entries in case of interruption
        if idx % 20 == 0:
            with open("ife_cache.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  -- saved checkpoint ({done} done, {failed} failed) --")

        time.sleep(0.3)  # stay under rate limits

    with open("ife_cache.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Generated: {done} | Failed: {failed}")


if __name__ == "__main__":
    main()
