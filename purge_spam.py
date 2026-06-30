"""Targeted purge: remove known bad entries and junk patterns."""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Exact title substring matches for known bad entries
BAD_TITLE_SUBSTRINGS = [
    "DALE WAS ACTING REALLY STRANGE",
    "Kannur Squad Review",
]

# Junk title regex — AI drama, non-aviation, spam
_JUNK_RE = re.compile(
    r'\bzerg\b'
    r'|\bevolution\s+system\b'
    r'|\bant\s+(soldier|empire|colony|queen)\b'
    r'|\bhatch(es|ing)?\s+\d'
    r'|\bmarried\s+the\s+(ceo|boss|president|king|prince|tycoon)\b'
    r'|\bdiscovered\s+\d+\s*bros\b'
    r'|\bsecret\s+heiress\b'
    r'|\breborn\s+in\s+\d{4}\b'
    r'|\bnecromancer\b'
    r'|\bweak(ling|est)?\s+awaken'
    r'|\binfinite\s+weapon\b'
    r'|\bsystem\s+builds?\b'
    r'|\blanded\s+a\s+burning\s+jet\b'
    r'|\bpoisoned\s+trial\b'
    r'|\bhorror\s+movie\b'
    r'|\bfree\s+horror\b'
    r'|\bsailing\s+catamaran\b'
    r'|\bsuperyacht\b'
    r'|\bcruise\s+ship\s+review\b'
    r'|\broblox\b'
    r'|\bworld\s+news\s+tonight\b'
    r'|\btim\s+dillon\s+show\b'
    r'|\bnational\s+geo(graphic)?\b'
    r'|\bnikola\s+tesla\b'
    r'|\bdrone\s+review\b'
    r'|\bdanish\s+practice\b'
    r'|\bswedish\s+practice\b'
    r'|\bnorwegian\s+practice\b'
    r'|\benglish\s+practice\s+lesson\b'
    r'|\blearn\s+russian\b'
    r'|\bwife\s+(offered|threw|poisoned|lied)\b'
    r'|\bhusband\s+lied\b'
    r'|\bshe\s+was\s+a\s+substitute\b'
    r'|\bmy\s+(rich\s+)?wife\s+(offered|threw|paid)\b'
    r'|\bbankrupt\s+ceo\b'
    r'|\bceo\s+heard\s+my\s+mind\b'
    r'|\bmillionaire\s+just\s+by\b'
    r'|\bthe\s+f.rank\s+weakling\b'
    r'|\boverpowered\s+(necromancer|system|bloodline)\b'
    r'|\bdiscovered.*castle\b'
    r'|\bsquad\s+review\s+@\w'
    r'|\bmeet,?\s+marry,?\s+murder\b',
    re.IGNORECASE,
)


def _is_spam(title: str) -> bool:
    if len(re.findall(r'#\w+', title)) >= 4:
        return True
    tl = title.lower()
    return "#shorts" in tl or "#short " in tl or "| shorts" in tl


with open("ife_cache.json", encoding="utf-8") as f:
    data = json.load(f)

before = len(data["reviews"])
kept, removed = [], []

for r in data["reviews"]:
    title = r.get("title", "")
    bad = (
        _is_spam(title)
        or _JUNK_RE.search(title)
        or any(s in title for s in BAD_TITLE_SUBSTRINGS)
    )
    if bad:
        removed.append(title[:90])
    else:
        kept.append(r)

data["reviews"] = kept

with open("ife_cache.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Removed {before - len(kept)} entries ({len(kept)} remain)")
for t in removed:
    print(f"  - {t}")
