from __future__ import annotations

import csv
import html
import re
from html.parser import HTMLParser
from pathlib import Path
from datetime import date, timedelta

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


def infer_occurrence_date(row: dict, clock_time: str) -> tuple[str, str]:
    """Infer a calendar date from report date and an explicit clock time."""
    report_date = row.get("date", "")
    if not clock_time:
        return "", "no_explicit_occurrence_time"
    try:
        published_day = date.fromisoformat(report_date)
    except (TypeError, ValueError):
        return "", "publication_date_unusable"
    kind = " ".join(str(row.get(key, "")) for key in
                    ("type_original", "headline", "description")).casefold()
    is_night_summary = "natt" in kind and (
        row.get("is_summary", "").casefold() == "true" or "sammanfattning" in kind
    )
    hour, _minute = (int(part) for part in clock_time.replace(".", ":").split(":"))
    if is_night_summary and hour >= 22:
        return (published_day - timedelta(days=1)).isoformat(), "night_summary_previous_evening"
    if is_night_summary and hour < 7:
        return published_day.isoformat(), "night_summary_after_midnight"
    return published_day.isoformat(), "dated_report_explicit_time"

def extract(row: dict) -> list[dict]:
    body = clean(row.get("content") or row.get("description") or row.get("headline") or "")
    lines = [line.strip(" -–—") for line in body.splitlines() if line.strip()]
    out = []
    seen = set()

    # Split only on explicit time markers that introduce a new wildlife
    # statement. Other clock times (for example a period/range in prose) must
    # not create empty or duplicate child rows.
    time_matches = list(TIME_RE.finditer(body))
    statement_starts = []
    for tm in time_matches:
        tail = body[tm.start():]
        next_time = TIME_RE.search(body, tm.end())
        end = next_time.start() if next_time else len(body)
        segment = tail[:end - tm.start()].strip(" \n-–—")
        prefix = body[max(0, tm.start() - 40):tm.start()]
        if not WILDLIFE_RE.search(segment):
            continue
        # Require the time to be a statement lead-in, not a time mentioned
        # inside a sentence. Accept start of text, punctuation, or whitespace
        # after a line break / sentence boundary.
        if prefix and not re.search(r"(?:^|[\n.!?])\s*$", prefix):
            continue
        statement_starts.append(tm)

    for i, tm in enumerate(statement_starts):
        segment_end = statement_starts[i + 1].start() if i + 1 < len(statement_starts) else len(body)
        segment = body[tm.start():segment_end].strip(" \n-–—")
        occurrence_time = tm.group("time").replace(".", ":")
        occurrence_date, date_basis = infer_occurrence_date(row, occurrence_time)
        key = (occurrence_time, segment.casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "parent_event_id": row.get("event_id", ""),
            "publication_date": row.get("date", ""),
            "occurrence_date": occurrence_date,
            "occurrence_date_basis": date_basis,
            "occurrence_time": occurrence_time,
            "municipality": municipality(segment),
            "species": species(segment),
            "place_text": segment[:500],
            "description": segment,
            "source_link": row.get("external_source_link", ""),
            "extraction_method": "wildlife_time_segment_v2",
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
                    "occurrence_date_basis": "count_without_time",
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
    # Stable child identity within the parent source event. These indices
    # identify extracted statements, not confirmed collision counts.
    for index, item in enumerate(out, start=1):
        item["occurrence_index"] = index

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
        "parent_event_id", "publication_date", "occurrence_date", "occurrence_date_basis", "occurrence_time",
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
