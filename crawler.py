import html
import json
import time
import requests
import urllib.parse
import urllib.robotparser
from bs4 import BeautifulSoup
from collections import deque
from typing import List


class SimpleCrawler:
    """A minimal, polite web crawler.

    - Respects robots.txt when available
    - Uses a delay between requests
    - Optionally restricts crawling to the start domain
    """

    def __init__(self, start_url: str, max_pages: int = 100, max_depth: int = 2, delay: float = 1.0, same_domain: bool = True, verify_ssl: bool = True):
        self.start_url = start_url
        parsed = urllib.parse.urlparse(start_url)
        self.base_domain = parsed.netloc
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay = delay
        self.same_domain = same_domain
        self.verify_ssl = verify_ssl
        self.visited = set()
        self.results = []

        # robots.txt
        self.rp = urllib.robotparser.RobotFileParser()
        try:
            robots_url = urllib.parse.urljoin(start_url, "/robots.txt")
            self.rp.set_url(robots_url)
            self.rp.read()
        except Exception:
            pass

    def crawl(self) -> List[dict]:
        queue = deque()
        queue.append((self.start_url, 0))

        while queue and len(self.visited) < self.max_pages:
            url, depth = queue.popleft()

            if url in self.visited:
                continue
            if depth > self.max_depth:
                continue
            if not self._allowed_by_robots(url):
                continue

            try:
                time.sleep(self.delay)
                html = self._fetch(url)
            except Exception:
                continue

            self.visited.add(url)
            title, links = self._extract_links(html, url)
            metadata = self._extract_meta(html, url)
            self.results.append({"url": url, "title": title, **metadata})

            for link in links:
                if self.same_domain:
                    parsed = urllib.parse.urlparse(link)
                    if parsed.netloc != self.base_domain:
                        continue
                if link not in self.visited:
                    queue.append((link, depth + 1))

        return self.results

    def _allowed_by_robots(self, url: str) -> bool:
        try:
            return self.rp.can_fetch("*", url)
        except Exception:
            return True

    def _fetch(self, url: str) -> str:
        headers = {"User-Agent": "SimpleCrawler/1.0 (+https://example.com)"}
        resp = requests.get(url, headers=headers, timeout=10, verify=self.verify_ssl)
        resp.raise_for_status()
        return resp.text

    def _extract_links(self, html: str, base_url: str):
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        links = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            parsed = urllib.parse.urlparse(href)
            if parsed.scheme in ("http", "https"):
                full = href
            else:
                full = urllib.parse.urljoin(base_url, href)
            full = urllib.parse.urldefrag(full)[0]
            links.add(full)

        return title, list(links)

    def _extract_meta(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        metadata = {}

        # Extract important fields
        meta_dict = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name") or tag.get("property")
            if not name:
                continue
            name = name.strip().lower()
            content = tag.get("content", "").strip()
            if content:
                meta_dict[name] = content

        # Important tags: keywords
        if "keywords" in meta_dict:
            tags = [t.strip() for t in meta_dict["keywords"].split(",")]
            metadata["tags"] = tags[:5]  # Limit to 5 tags

        # Important keywords: from description
        if "description" in meta_dict:
            metadata["description"] = meta_dict["description"]

        # Year made: from publish date or article published time
        year = None
        year_keys = [
            "article:published_time",
            "publish_date",
            "published_time",
            "datepublished",
            "og:video:release_date",
            "uploaddate",
            "dateuploaded",
        ]
        for key in year_keys:
            if key in meta_dict:
                try:
                    year_str = meta_dict[key][:4]
                    year = int(year_str)
                    break
                except (ValueError, IndexError):
                    pass
        if year:
            metadata["year"] = year

        # YouTube captions/transcript
        captions = self._extract_youtube_captions(html)
        if captions:
            metadata["youtube_captions"] = captions
            has_transcript = any("transcript" in cap for cap in captions if isinstance(cap, dict))
            metadata["transcript_available"] = "Yes" if has_transcript else "No (captions available)"
        else:
            metadata["transcript_available"] = "No"

        return metadata

    def _extract_youtube_captions(self, html: str) -> list:
        captions = []

        def extract_json_array(key: str):
            idx = html.find(key)
            if idx == -1:
                return None
            start = html.find("[", idx)
            if start == -1:
                return None
            depth = 0
            in_string = False
            escaped = False
            for i in range(start, len(html)):
                ch = html[i]
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == "[":
                        depth += 1
                    elif ch == "]":
                        depth -= 1
                        if depth == 0:
                            return html[start : i + 1]
            return None

        def parse_name(value):
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                if "simpleText" in value:
                    return value["simpleText"]
                if "runs" in value and isinstance(value["runs"], list):
                    return "".join([run.get("text", "") for run in value["runs"]])
            return None

        for key in ["\"captionTracks\":", "captionTracks\":"]:
            fragment = extract_json_array(key)
            if not fragment:
                continue
            try:
                data = json.loads(fragment)
            except Exception:
                continue
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    base_url = item.get("baseUrl")
                    caption = {
                        "baseUrl": base_url,
                        "name": parse_name(item.get("name")),
                        "languageCode": item.get("languageCode"),
                        "kind": item.get("kind"),
                        "vssId": item.get("vssId"),
                    }
                    if base_url:
                        try:
                            caption_text = self._fetch_caption_transcript(base_url)
                            if caption_text:
                                caption["transcript"] = caption_text
                        except Exception:
                            caption["transcript_error"] = "Unable to fetch transcript"
                    captions.append(caption)
                break

        return captions

    def _fetch_caption_transcript(self, url: str) -> str:
        headers = {"User-Agent": "SimpleCrawler/1.0 (+https://example.com)"}
        resp = requests.get(url, headers=headers, timeout=10, verify=self.verify_ssl)
        resp.raise_for_status()
        return self._parse_vtt(resp.text)

    def _parse_vtt(self, content: str) -> str:
        lines = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("WEBVTT"):
                continue
            if line.startswith("NOTE"):
                continue
            if line.startswith("STYLE"):
                continue
            if "-->" in line:
                continue
            if line.isdigit():
                continue
            lines.append(html.unescape(line))
        return " ".join(lines).strip()

    def save_results(self, path: str):
        import json

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
