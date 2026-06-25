import argparse
import json
from crawler import SimpleCrawler


def format_results_as_table(results: list) -> str:
    """Format results as a readable table."""
    if not results:
        return "No results to display."

    lines = []
    lines.append("=" * 150)
    lines.append(f"{'URL':<60} | {'Title':<30} | {'Tags':<20} | {'Year':<6} | {'Transcript':<20}")
    lines.append("=" * 150)

    for item in results:
        url = item.get("url", "")[:60]
        title = item.get("title", "")[:30]
        
        tags = ", ".join(item.get("tags", [])[:3]) if "tags" in item else "-"
        tags = tags[:20]
        
        year = str(item.get("year", "-"))[:6]
        
        # Check for transcript
        transcript_status = "No transcript available"
        if "youtube_captions" in item and item["youtube_captions"]:
            captions = item["youtube_captions"]
            has_transcript = any("transcript" in cap for cap in captions if isinstance(cap, dict))
            transcript_status = "Transcript available" if has_transcript else "No transcript"
        
        lines.append(f"{url:<60} | {title:<30} | {tags:<20} | {year:<6} | {transcript_status:<20}")
        
        # Add transcript details if available
        if "youtube_captions" in item:
            for cap in item["youtube_captions"]:
                if isinstance(cap, dict) and "transcript" in cap:
                    transcript_text = cap["transcript"][:100] + "..." if len(cap.get("transcript", "")) > 100 else cap.get("transcript", "")
                    lang = cap.get("languageCode", "unknown")
                    lines.append(f"  └─ [{lang}] Transcript: {transcript_text}")
        
        lines.append("-" * 150)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Simple web crawler")
    parser.add_argument("start_url")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--output", default="results.json")
    parser.add_argument("--same-domain", action="store_true")
    parser.add_argument("--no-verify", action="store_true", help="Disable SSL certificate verification for testing")
    args = parser.parse_args()

    c = SimpleCrawler(
        args.start_url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        delay=args.delay,
        same_domain=args.same_domain,
        verify_ssl=not args.no_verify,
    )
    results = c.crawl()
    c.save_results(args.output)
    
    # Print table format
    print(format_results_as_table(results))
    print(f"\nDone. Crawled {len(results)} pages. Results saved to {args.output}")


if __name__ == "__main__":
    main()
