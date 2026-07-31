"""
Translate non-English transcript captions to English using Google Translate
(via the free `deep-translator` library — no API key required).

For every review, each caption line that is NOT already English gets an added
`text_en` field (the English translation) and a `lang` field (detected source
language). The original `text` is left untouched. Lines already in English are
marked lang="en" and skipped.

Detection: lines with non-Latin script (CJK / Arabic / Cyrillic / Indic …) are
always translated. Pure-ASCII/Latin lines are assumed English and skipped to
avoid pointless calls (the transcripts are overwhelmingly English otherwise).
Pass --all to also send accented Latin lines (French/German/Spanish) through
Google's auto-detect.

Run:  python translate_captions.py             (translate non-Latin lines)
      python translate_captions.py --limit 30  (test on the first 30)
      python translate_captions.py --all       (also translate accented-Latin)
"""
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from deep_translator import GoogleTranslator

CACHE = Path(__file__).parent / "ife_cache.json"

# A line with several non-Latin chars (CJK / Arabic / Cyrillic / Thai / Indic …)
# is certainly non-English. Emoji, punctuation and Latin-1 accents are excluded
# from this test so English-with-emoji lines aren't flagged.
_NONLATIN = re.compile(r"[^\x00-\x7FÀ-ɏ -➿\U0001F000-\U0001FAFF]")


def _has_nonlatin(s):
    return len(_NONLATIN.findall(s or "")) >= 2


def _guess_lang(s):
    """Best-effort source-language guess from character ranges (no network)."""
    s = s or ""
    if re.search(r"[぀-ヿ]", s):
        return "ja"                                  # hiragana/katakana
    if re.search(r"[가-힯]", s):
        return "ko"                                  # hangul
    if re.search(r"[؀-ۿ]", s):
        return "ar"                                  # arabic
    if re.search(r"[Ѐ-ӿ]", s):
        return "ru"                                  # cyrillic
    if re.search(r"[ఀ-౿]", s):
        return "te"                                  # telugu
    if re.search(r"[ऀ-ॿ]", s):
        return "hi"                                  # devanagari
    if re.search(r"[฀-๿]", s):
        return "th"                                  # thai
    if re.search(r"[一-鿿]", s):
        return "zh"                                  # cjk (chinese, or shared kanji)
    return "und"


def _needs_translation(s, include_latin):
    s = (s or "").strip()
    if len(s) < 3:
        return False
    if _has_nonlatin(s):
        return True
    if include_latin:
        # accented Latin that might be non-English (café, écran, für…)
        return bool(re.search(r"[À-ÿ]", s))
    return False


def main():
    argv = sys.argv[1:]
    include_latin = "--all" in argv
    limit = None
    if "--limit" in argv:
        try:
            limit = int(argv[argv.index("--limit") + 1])
        except Exception:
            pass

    data = json.loads(CACHE.read_text(encoding="utf-8"))
    reviews = data.get("reviews", [])

    # Collect every text item needing translation as a direct dict reference,
    # so one pass covers video titles, captions and YouTube comments.
    # Each entry: (obj_dict, text, en_field, lang_field). Titles go FIRST so a
    # --limit run still covers them all.
    pending = []
    for r in reviews:
        t = (r.get("title") or "").strip()
        if not r.get("title_en") and r.get("title_lang") != "en":
            if _needs_translation(t, include_latin):
                pending.append((r, t, "title_en", "title_lang"))
            elif len(t) >= 3 and not _has_nonlatin(t):
                r["title_lang"] = "en"
    for r in reviews:
        for c in (r.get("captions") or []):
            if c.get("text_en") or c.get("lang") == "en":
                continue
            t = (c.get("text") or "").strip()
            if _needs_translation(t, include_latin):
                pending.append((c, t, "text_en", "lang"))
            elif len(t) >= 3 and not _has_nonlatin(t):
                c["lang"] = "en"
        for c in (r.get("yt_comments") or []):
            if c.get("text_en") or c.get("lang") == "en":
                continue
            t = (c.get("text") or "").strip()
            if _needs_translation(t, include_latin):
                pending.append((c, t, "text_en", "lang"))
            elif len(t) >= 3 and not _has_nonlatin(t):
                c["lang"] = "en"

    if limit:
        pending = pending[:limit]
    print(f"Items to translate (titles + captions + comments): {len(pending)}")
    if not pending:
        CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Nothing to translate.")
        return

    translator = GoogleTranslator(source="auto", target="en")
    done = fail = 0
    langs = {}
    for n, (obj, t, en_field, lang_field) in enumerate(pending, 1):
        try:
            en = translator.translate(t)
            obj[lang_field] = _guess_lang(t)
            if en and en.strip().lower() != t.strip().lower():
                obj[en_field] = en
                langs[obj[lang_field]] = langs.get(obj[lang_field], 0) + 1
            done += 1
        except Exception as e:
            fail += 1
            print(f"  ! item {n} failed: {type(e).__name__} {str(e)[:80]}")
        if n % 20 == 0:
            CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  [{n}/{len(pending)}] translated (fail={fail})")
        time.sleep(0.1)  # be gentle with the free endpoint

    CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. Translated {done} items (failed {fail}).")
    print(f"By source language: {dict(sorted(langs.items(), key=lambda x:-x[1]))}")
    print(f"Saved {CACHE.name}.")


if __name__ == "__main__":
    main()
