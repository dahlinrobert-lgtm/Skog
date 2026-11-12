#!/usr/bin/env python3
"""Generate explainable Police–NVR temporal/text match candidates; never auto-confirms."""
from __future__ import annotations
import argparse, csv, json, re
from collections import Counter
from datetime import datetime
from pathlib import Path

TIME_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3])[.:]([0-5]\d)(?!\d)")
ROAD_RE = re.compile(r"\b(?:e\s?4|e\s?10|e\s?45|riksväg\s+\d+|länsväg\s+\d+)\b", re.I)
STOP = {"och","med","utan","vid","mellan","på","i","en","ett","det","som","för","från","till","luleå","viltolycka","olycka","personbil","lastbil","polis","inga","uppgifter","personskador","rapporterats","rapporteras"}

def norm(value):
    return re.sub(r"\s+", " ", (value or "").casefold().replace("–","-").replace("—","-")).strip()

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

def build_candidates(police_rows, nvr_rows, max_time_delta_minutes=180):
    # NVR rows must already be event-level (one row per year-qualified accident_key).
    nvr = []
    for row in nvr_rows:
        dts = [parse_dt(x) for x in split_values(row.get("event_datetime_values"))]
        dts = [x for x in dts if x]
        if not dts: continue
        nvr.append({**row, "_dts": dts, "_municipalities": {norm(x) for x in split_values(row.get("source_municipalities"))},
                    "_species": {norm(x) for x in split_values(row.get("species"))}})
    output = []
    for p in police_rows:
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
            n_days = {x.date() for x in n["_dts"]}
            if day not in n_days: continue
            n_species = n["_species"]
            species_match = bool(p_species and p_species in n_species)
            n_roads, n_words = text_terms(" ".join([n.get("species",""), n.get("source_municipalities",""), n.get("road_name",""), n.get("place_name","")]))
            # NVR event-level builder does not yet contain road/place labels; keep these empty unless enriched upstream.
            shared_roads = sorted(p_roads & n_roads)
            shared_terms = sorted((p_words & n_words) - {"luleå"})
            # Missing Police time is unavailable, not a time conflict against a known NVR time.
            delta = min((abs((pdt - ndt).total_seconds()) / 60 for ndt in n["_dts"] if pdt and ndt.date() == day), default=None)
            if pdt is None: time_band = "same_date_time_unavailable"
            elif delta is not None and delta <= 15: time_band = "within_15m"
            elif delta is not None and delta <= 60: time_band = "within_1h"
            elif delta is not None and delta <= max_time_delta_minutes: time_band = "within_configured_window"
            elif delta is not None: time_band = "same_date_time_conflict"
            else: time_band = "same_date_time_unavailable"
            # Transparent ordinal score: date is the candidate-generation gate, not proof.
            score = 30 + (30 if delta is not None and delta <= 15 else 20 if delta is not None and delta <= 60 else 10 if delta is not None and delta <= max_time_delta_minutes else 0)
            score += 20 if species_match else 0
            score += 15 if shared_roads else 0
            score += 5 if shared_terms else 0
            if pdt is None: status = "date_only_weak_candidate"
            elif delta is not None and delta > max_time_delta_minutes: status = "same_date_time_conflict_review"
            else: status = "temporal_candidate_review"
            output.append({
                "police_event_id": p.get("parent_event_id",""), "police_occurrence_date": pdate,
                "police_occurrence_date_basis": p.get("occurrence_date_basis",""),
                "police_occurrence_time": ptime, "police_municipality": p.get("municipality",""),
                "police_species": p.get("species",""), "police_text": p.get("description",""),
                "nvr_accident_key": n.get("accident_key",""), "nvr_olycks_id": n.get("OlycksID",""),
                "nvr_event_datetime_values": n.get("event_datetime_values",""),
                "nvr_municipalities": n.get("source_municipalities",""), "nvr_species": n.get("species",""),
                "same_date": True, "time_delta_minutes": "" if delta is None else round(delta,1),
                "time_band": time_band, "species_match": species_match,
                "shared_road_terms": ";".join(shared_roads), "shared_text_terms": ";".join(shared_terms[:10]),
                "candidate_score": score, "candidate_status": status,
                "geographic_match_used": False, "review_status": "unreviewed",
            })
    output.sort(key=lambda r:(r["police_occurrence_date"],r["police_event_id"],-r["candidate_score"],r["nvr_accident_key"]))
    return output

def read_csv(path, delimiter=",", encoding="utf-8-sig"):
    with path.open(encoding=encoding, newline="") as f: return list(csv.DictReader(f, delimiter=delimiter))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--police",type=Path,required=True)
    ap.add_argument("--nvr",type=Path,required=True,help="Event-level NVR CSV from build_nvr_accident_points.py")
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--max-time-delta-minutes",type=int,default=180)
    args=ap.parse_args()
    if args.max_time_delta_minutes < 0: ap.error("--max-time-delta-minutes must be non-negative")
    rows=build_candidates(read_csv(args.police),read_csv(args.nvr))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]) if rows else ["police_event_id","police_occurrence_date","nvr_accident_key","same_date","time_delta_minutes","candidate_score","candidate_status","review_status"]
    with args.output.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    print(json.dumps({"status":"completed","candidate_pairs":len(rows),"status_counts":dict(Counter(r["candidate_status"] for r in rows)),"output":str(args.output)},ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
