#!/usr/bin/env python3
"""Generate explainable Police–NVR temporal/text match candidates; never auto-confirms."""
from __future__ import annotations
import argparse, csv, json, re
from collections import Counter
from datetime import datetime
from pathlib import Path

TIME_RE = re.compile(r"(?<!\\d)([01]?\\d|2[0-3])[.:]([0-5]\\d)(?!\\d)")
ROAD_RE = re.compile(r"\\b(?:e\\s?4|e\\s?10|e\\s?45|riksväg\\s+\\d+|länsväg\\s+\\d+)\\b", re.I)
STOP = {"och","med","utan","vid","mellan","på","i","en","ett","det","som","för","från","till","luleå","viltolycka","olycka","personbil","lastbil","polis","inga","uppgifter","personskador","rapporterats","rapporteras"}

def norm(value):
    return re.sub(r"\\s+", " ", (value or "").casefold().replace("–","-").replace("—","-")).strip()

def parse_dt(value):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try: return datetime.strptime(value, fmt)
        except ValueError: pass
    return None

def extract_times(text):
    return sorted({f"{int(h):02d}:{m}" for h,m in TIME_RE.findall(text or "")})

def text_terms(text):
    value = norm(text)
    roads = {norm(x) for x in ROAD_RE.findall(value)}
    words = {w for w in re.findall(r"[a-zåäö0-9]+", value) if len(w) >= 4 and w not in STOP}
    return roads, words

def split_values(value):
    return [x.strip() for x in (value or "").split(";") if x.strip()]

def clock_delta_minutes(left, right):
    """Absolute wall-clock difference, ignoring the calendar date."""
    a = left.hour * 60 + left.minute
    b = right.hour * 60 + right.minute
    return abs(a - b)

def elapsed_delta_minutes(left, right):
    """Absolute elapsed-time difference between complete timestamps."""
    return abs((left - right).total_seconds()) / 60

def build_candidates(police_rows, nvr_rows, max_time_delta_minutes=180, date_window_days=1):
    # NVR rows must already be event-level (one row per year-qualified accident_key).
    nvr = []
    for row in nvr_rows:
        dts = [parse_dt(x) for x in split_values(row.get("event_datetime_values"))]
        dts = [x for x in dts if x]
        if not dts: continue
        nvr.append({**row, "_dts": dts, "_municipalities": {norm(x) for x in split_values(row.get("source_municipalities"))},
                    "_species": {norm(x) for x in split_values(row.get("species"))}})
    output = []
    for police_row_index, p in enumerate(police_rows, start=1):
        occurrence_index = (p.get("occurrence_index") or "").strip()
        police_candidate_id = f"{p.get('parent_event_id', '')}:{occurrence_index or f'row-{police_row_index}'}"
        pdate = (p.get("occurrence_date") or "").strip()
        try: day = datetime.strptime(pdate, "%Y-%m-%d").date()
        except ValueError: continue
        if norm(p.get("municipality")) != "luleå": continue
        ptime = (p.get("occurrence_time") or "").strip()
        if not ptime:
            times = extract_times(p.get("description") or "")
            ptime = times[0] if len(times) == 1 else ""
        pdt = parse_dt(f"{pdate} {ptime}") if ptime else None
        p_species = norm(p.get("species"))
        p_roads, p_words = text_terms(" ".join([p.get("description",""), p.get("place_text","")]))
        for n in nvr:
            if "luleå" not in n["_municipalities"]: continue
            eligible = []
            for ndt in n["_dts"]:
                date_offset = (ndt.date() - day).days
                if date_offset < 0 or date_offset > date_window_days: continue
                if pdt is None:
                    delta = None
                    clock_delta = None
                else:
                    # Always classify by actual elapsed time. Keep wall-clock
                    # difference separately for diagnosis across midnight.
                    delta = elapsed_delta_minutes(pdt, ndt)
                    clock_delta = clock_delta_minutes(pdt, ndt)
                eligible.append((delta if delta is not None else float("inf"), date_offset, ndt, delta, clock_delta))
            if not eligible: continue
            _, date_offset, best_ndt, delta, clock_delta = min(eligible, key=lambda x:(x[0], x[1], x[2]))
            n_species = n["_species"]
            species_match = bool(p_species and p_species in n_species)
            n_roads, n_words = text_terms(" ".join([n.get("species",""), n.get("source_municipalities",""), n.get("road_name",""), n.get("place_name","")]))
            shared_roads = sorted(p_roads & n_roads)
            shared_terms = sorted((p_words & n_words) - {"luleå"})
            if pdt is None: time_band = "time_unavailable"
            elif delta <= 15: time_band = "within_15m"
            elif delta <= 60: time_band = "within_1h"
            elif delta <= max_time_delta_minutes: time_band = "within_configured_window"
            else: time_band = "time_conflict"
            score = 30 + (30 if delta is not None and delta <= 15 else 20 if delta is not None and delta <= 60 else 10 if delta is not None and delta <= max_time_delta_minutes else 0)
            score += 20 if species_match else 0
            score += 15 if shared_roads else 0
            score += 5 if shared_terms else 0
            if pdt is None: status = "date_only_weak_candidate" if date_offset == 0 else "next_day_date_only_review"
            elif date_offset == 1 and delta <= max_time_delta_minutes: status = "next_day_rollover_review"
            elif date_offset == 1: status = "next_day_time_conflict_review"
            elif delta > max_time_delta_minutes: status = "same_date_time_conflict_review"
            else: status = "temporal_candidate_review"
            output.append({
                "police_candidate_id": police_candidate_id,
                "police_event_id": p.get("parent_event_id",""), "police_occurrence_index": occurrence_index,
                "police_occurrence_date": pdate,
                "police_occurrence_date_basis": p.get("occurrence_date_basis",""),
                "police_occurrence_time": ptime, "police_municipality": p.get("municipality",""),
                "police_species": p.get("species",""), "police_text": p.get("description",""),
                "nvr_accident_key": n.get("accident_key",""), "nvr_olycks_id": n.get("OlycksID",""),
                "nvr_event_datetime_values": n.get("event_datetime_values",""),
                "nvr_municipalities": n.get("source_municipalities",""), "nvr_species": n.get("species",""),
                "same_date": date_offset == 0, "date_offset_days": date_offset,
                "date_relation": "same_date" if date_offset == 0 else "nvr_next_day",
                "time_delta_minutes": "" if delta is None else round(delta,1),
                "absolute_datetime_delta_minutes": "" if delta is None else round(delta,1),
                "clock_time_delta_minutes": "" if clock_delta is None else round(clock_delta,1),
                "time_band": time_band, "species_match": species_match,
                "shared_road_terms": ";".join(shared_roads), "shared_text_terms": ";".join(shared_terms[:10]),
                "candidate_score": score, "candidate_status": status,
                "geographic_match_used": False, "review_status": "unreviewed",
            })
    output.sort(key=lambda r:(r["police_occurrence_date"],r["police_event_id"],-r["candidate_score"],r["nvr_accident_key"]))
    return output

def build_audit_report(police_rows, nvr_rows, candidates, max_time_delta_minutes=180, date_window_days=1):
    """Summarize candidate multiplicity, including source rows with zero matches."""
    police_ids = []
    for index, row in enumerate(police_rows, start=1):
        occurrence_index = (row.get("occurrence_index") or "").strip()
        police_ids.append(f"{row.get('parent_event_id', '')}:{occurrence_index or f'row-{index}'}")
    police_counts = Counter(row["police_candidate_id"] for row in candidates)
    nvr_keys = sorted({row.get("accident_key", "") for row in nvr_rows if row.get("accident_key")})
    nvr_counts = Counter(row["nvr_accident_key"] for row in candidates)
    def distribution(keys, counts):
        values = [counts.get(key, 0) for key in keys]
        return {"zero_candidates": sum(value == 0 for value in values), "one_candidate": sum(value == 1 for value in values), "multiple_candidates": sum(value > 1 for value in values)}
    valid_dates = 0
    for row in police_rows:
        try:
            datetime.strptime((row.get("occurrence_date") or "").strip(), "%Y-%m-%d")
            valid_dates += 1
        except ValueError: pass
    return {
        "schema_version": "1.1",
        "scope": "Luleå Police statements against event-level NVR rows",
        "police_statement_count": len(police_ids),
        "police_statements_with_valid_occurrence_date": valid_dates,
        "police_statements_without_valid_occurrence_date": len(police_ids) - valid_dates,
        "police_candidate_distribution": distribution(police_ids, police_counts),
        "nvr_event_count": len(nvr_keys),
        "nvr_event_candidate_distribution": distribution(nvr_keys, nvr_counts),
        "candidate_pair_count": len(candidates),
        "candidate_status_counts": dict(sorted(Counter(row["candidate_status"] for row in candidates).items())),
        "date_window_days_after_police_date": date_window_days,
        "max_time_delta_minutes": max_time_delta_minutes,
        "next_day_rollover_candidate_count": sum(row.get("date_offset_days") == 1 for row in candidates),
        "interpretation": "Police occurrence dates may be preliminary or one calendar day early. Time differences use absolute elapsed time between full timestamps; clock-time differences are diagnostic only. Next-day candidates remain review-only; no candidate is automatically confirmed. Zero candidates do not prove that no collision occurred.",
    }

def write_audit_report(report, path):
    """Write valid UTF-8 JSON with a real newline and a BOM for Windows PowerShell."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")

def read_csv(path, delimiter=",", encoding="utf-8-sig"):
    with path.open(encoding=encoding, newline="") as f: return list(csv.DictReader(f, delimiter=delimiter))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--police",type=Path,required=True)
    ap.add_argument("--nvr",type=Path,required=True,help="Event-level NVR CSV from build_nvr_accident_points.py")
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--max-time-delta-minutes",type=int,default=180)
    ap.add_argument("--date-window-days",type=int,default=1,help="Also consider NVR events up to this many calendar days after the Police date; default 1")
    ap.add_argument("--report",type=Path,help="Optional JSON audit report including zero/one/multiple candidate counts")
    args=ap.parse_args()
    if args.max_time_delta_minutes < 0: ap.error("--max-time-delta-minutes must be non-negative")
    if args.date_window_days < 0: ap.error("--date-window-days must be non-negative")
    police_rows=read_csv(args.police)
    nvr_rows=read_csv(args.nvr)
    rows=build_candidates(police_rows,nvr_rows,args.max_time_delta_minutes,args.date_window_days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]) if rows else ["police_candidate_id","police_event_id","police_occurrence_index","police_occurrence_date","nvr_accident_key","same_date","date_offset_days","date_relation","time_delta_minutes","candidate_score","candidate_status","review_status"]
    with args.output.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    summary={"status":"completed","candidate_pairs":len(rows),"status_counts":dict(Counter(r["candidate_status"] for r in rows)),"output":str(args.output)}
    if args.report:
        report=build_audit_report(police_rows,nvr_rows,rows,args.max_time_delta_minutes,args.date_window_days)
        write_audit_report(report, args.report)
        summary["report"]=str(args.report)
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
