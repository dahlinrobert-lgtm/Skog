from __future__ import annotations

import csv
import html
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "police_events"
EVENTS = DATA / "events.csv"
OUT = DATA / "wildlife_incidents.csv"

MUNICIPALITIES = [
    "Arvidsjaur", "Arjeplog", "Boden", "Gällivare", "Haparanda",
    "Jokkmokk", "Kalix", "Kiruna", "Luleå", "Pajala", "Piteå",
    "Älvsbyn", "Överkalix", "Övertorneå",
]
SPECIES = ("älg", "ren", "rådjur", "hjort", "vildsvin", "örn")
WILDLIFE_RE = re.compile(
    r"viltolyck|renolyck|älgolyck|rådjursolyck|hjortolyck|"
    r"kollider\w* med (?:en )?(?:älg|ren|rådjur|hjort)|"
    r"(?:älg|ren|rådjur|hjort)\w*.{0,60}(?:påkörd|påkö\w*|kollision)",
    re.I,
)
TIME_RE = re.compile(r"(?<!\d)(?P<time>[0-2]?\d[:.]\d{2})(?!\d)")
COUNT_RE = re.compile(
    r"(?i)\b(?P<count>\d{1,2}|en|ett|två|tre|fyra|fem|sex|sju|åtta|nio|tio)"
    r"\s+(?P<kind>viltolyck(?:a|or)|renpåkörning(?:ar)?)\b"
)
WORDS = {"en": 1, "ett": 1, "två": 2, "tre": 3, "fyra": 4, "fem": 5,
         "sex": 6, "sju": 7, "åtta": 8, "nio": 9, "tio": 10}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def text(self):
        return re.sub(r"\n{2,}", "\n", " ".join(self.parts).replace(" \n ", "\n")).strip()


def clean(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    raw = parser.text() if "<" in (value or "") else html.unescape(value or "")
    raw = raw.replace("\r", "\n")
    raw = re.sub(r"[ \t\xa0]+", " ", raw)
    return "\n".join(line.strip() for line in raw.splitlines() if line.strip())


def municipality(text: str) -> str:
    hits = [m for m in MUNICIPALITIES
            if re.search(r"(?<![a-zåäö])" + re.escape(m) + r"(?![a-zåäö])", text, re.I)]
    return hits[0] if len(hits) == 1 else ""


def species(text: str) -> str:
    hits = [s for s in SPECIES if re.search(r"\b" + s + r"\w*\b", text, re.I)]
    return ", ".join(hits)


def extract(row: dict) -> list[dict]:
    body = clean(row.get("content") or row.get("description") or row.get("headline") or "")
    lines = [line.strip(" -–—") for line in body.splitlines() if line.strip()]
    out = []
    seen = set()

    # A timed police summary often has one incident per line or paragraph.
    for i, line in enumerate(lines):
        if not WILDLIFE_RE.search(line):
            continue
        tm = TIME_RE.search(line)
        # Keep nearby following sentence(s) with the same occurrence until
        # the next explicit time marker; this preserves road/place context.
        details = [line]
        for nxt in lines[i + 1:i + 3]:
            if TIME_RE.search(nxt) and WILDLIFE_RE.search(nxt):
                break
            if TIME_RE.search(nxt) and not WILDLIFE_RE.search(nxt):
                break
            if len(" ".join(details)) < 500:
                details.append(nxt)
        segment = " ".join(details)
        key = (tm.group("time") if tm else "", segment.casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "parent_event_id": row.get("event_id", ""),
            "publication_date": row.get("date", ""),
            "occurrence_date": "",
            "occurrence_time": tm.group("time").replace(".", ":") if tm else "",
            "municipality": municipality(segment),
            "species": species(segment),
            "place_text": segment[:500],
            "description": segment,
            "source_link": row.get("external_source_link", ""),
            "extraction_method": "wildlife_text_line_v1",
            "confidence": "review",
            "occurrence_index": "",
        })

    # Explicit counts in summary prose are retained as separate count-only
    # candidates, never treated as independently located confirmed accidents.
    for line in lines:
        for match in COUNT_RE.finditer(line):
            token = match.group("count").casefold()
            count = int(token) if token.isdigit() else WORDS.get(token, 0)
            if count < 1:
                continue
            already = sum(1 for item in out if item["description"] == line)
            for idx in range(already + 1, count + 1):
                out.append({
                    "parent_event_id": row.get("event_id", ""),
                    "publication_date": row.get("date", ""),
                    "occurrence_date": "",
                    "occurrence_time": "",
                    "municipality": municipality(line),
                    "species": species(line),
                    "place_text": line[:500],
                    "description": line,
                    "source_link": row.get("external_source_link", ""),
                    "extraction_method": "explicit_count_v1",
                    "confidence": "low",
                    "occurrence_index": idx,
                })
    return out


def main():
    if not EVENTS.exists():
        raise SystemExit("events.csv saknas")
    with EVENTS.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    results = []
    for row in rows:
        if row.get("is_summary", "").casefold() == "true" or WILDLIFE_RE.search(
            " ".join(row.get(k, "") for k in ("type_original", "headline", "description", "content"))
        ):
            results.extend(extract(row))
    fields = [
        "parent_event_id", "publication_date", "occurrence_date", "occurrence_time",
        "municipality", "species", "place_text", "description", "source_link",
        "extraction_method", "confidence", "occurrence_index",
    ]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"source_events={len(rows)} extracted_wildlife_incidents={len(results)}")
    print("All extracted rows remain candidates requiring validation; source records are unchanged.")


if __name__ == "__main__":
    main()
