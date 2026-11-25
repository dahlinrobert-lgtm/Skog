#!/usr/bin/env python3
"""Build canonical planned-harvest and Samråd events with auditable candidate links.

The completed-harvest polygon layer is deliberately excluded: its Forebild/Efterbild
metadata identifies it as satellite-derived evidence. Satellite indications remain a
later, lower-priority input and are not promoted to completed-harvest events here.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LATEST = DATA / "latest.json"
HISTORY = DATA / "notification_history.json"
SAMRAD = DATA / "samrad_latest.json"
SAMRAD_SNAPSHOTS = DATA / "samrad_snapshots"
OUT = DATA / "harvest_event_bundle.json"
PLANNED_SOURCE = "skogsstyrelsen.harvest_notifications"
SAMRAD_SOURCE = "skogsstyrelsen.samrad"
INTERPRETATION_VERSION = "planned-harvest-event-v2"
TO_TM = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True).transform


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError, OverflowError):
        return None


def date_value(value: Any):
    stamp = timestamp(value)
    if not stamp:
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).date()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def usable_case_number(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw or raw.casefold() in {"visas ej", "visa ej", "saknas", "okänd", "null", "-", "undefined"}:
        return None
    return raw


def projected_area_geometry(geometry: dict[str, Any] | None):
    if not geometry:
        return None
    try:
        geom = transform(TO_TM, shape(geometry))
        if geom.is_empty:
            return None
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.geom_type in {"Point", "MultiPoint"}:
            geom = geom.buffer(25)
        elif geom.geom_type in {"LineString", "MultiLineString"}:
            geom = geom.buffer(15)
        return None if geom.is_empty else geom
    except Exception:
        return None


def municipality_key(props: dict[str, Any]) -> str | None:
    code = str(props.get("Kommunnr") or "").strip()
    if code:
        return code
    name = str(props.get("Kommun") or "").strip().casefold()
    return name or None



def samrad_snapshot_is_complete(snapshot: dict[str, Any]) -> bool:
    """Accept only structurally complete successful snapshots for history."""
    if snapshot.get("source_id") != SAMRAD_SOURCE or snapshot.get("status") != "success":
        return False
    if not timestamp(snapshot.get("checked_at")) or not str(snapshot.get("scope_hash") or "").strip():
        return False
    layers = snapshot.get("layers")
    counts = snapshot.get("counts")
    if not isinstance(layers, dict) or not isinstance(counts, dict):
        return False
    for name in ("points", "lines", "areas"):
        layer = layers.get(name)
        count = counts.get(name)
        if not isinstance(layer, dict) or layer.get("status") != "success" or not isinstance(count, dict):
            return False
        features = layer.get("features")
        if not isinstance(features, list) or not features:
            # Empty layers are valid when the collector explicitly reports zero rows.
            if features != [] or count.get("records_in_scope") != 0:
                return False
        required_ints = ("pages", "records_fetched_in_envelope", "records_in_scope",
                         "records_outside_scope", "records_missing_geometry", "records_geometry_error")
        if any(not isinstance(count.get(key), int) for key in required_ints):
            return False
        if count["pages"] < 1 or count["records_in_scope"] != len(features):
            return False
        if count["records_missing_geometry"] != 0 or count["records_geometry_error"] != 0:
            return False
        if count["records_fetched_in_envelope"] != count["records_in_scope"] + count["records_outside_scope"]:
            return False
    return True


def load_samrad_snapshot_archive(directory: Path = SAMRAD_SNAPSHOTS) -> list[tuple[str, dict[str, Any]]]:
    """Read immutable dated snapshots; malformed archive files fail closed."""
    if not directory.exists():
        return []
    result: list[tuple[str, dict[str, Any]]] = []
    pattern = re.compile(r"^samrad_(\d{8}T\d{6}Z)\.json\.gz$")
    for path in sorted(directory.glob("samrad_*.json.gz")):
        if not pattern.match(path.name):
            continue
        try:
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, EOFError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read archived Samråd snapshot {path.name}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Archived Samråd snapshot is not an object: {path.name}")
        result.append((path.relative_to(ROOT).as_posix(), payload))
    return result


def build_samrad_history(
    snapshots: list[tuple[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build one event per stable case key and retain each distinct source version."""
    source_runs: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    samrad_index: list[dict[str, Any]] = []
    cases: dict[str, list[dict[str, Any]]] = {}
    seen_snapshot_keys: set[tuple[str, str, str]] = set()
    seen_observation_versions: set[tuple[str, str]] = set()

    for snapshot_path, snapshot in sorted(snapshots, key=lambda row: timestamp(row[1].get("checked_at")) or ""):
        checked = timestamp(snapshot.get("checked_at"))
        scope_hash = str(snapshot.get("scope_hash") or "")
        if not samrad_snapshot_is_complete(snapshot):
            # Keep partial attempts out of history and, critically, out of absence reasoning.
            continue
        snapshot_digest = canonical_hash(snapshot)
        snapshot_key = (checked or "", scope_hash, snapshot_digest)
        if snapshot_key in seen_snapshot_keys:
            continue
        seen_snapshot_keys.add(snapshot_key)
        layers = snapshot["layers"]
        layer_features = [
            (layer_name, feature)
            for layer_name in ("points", "lines", "areas")
            for feature in layers[layer_name]["features"]
        ]
        run_id = f"{SAMRAD_SOURCE}:{checked}:{scope_hash[:12]}:{snapshot_digest[:12]}"
        source_runs.append({
            "run_id": run_id,
            "source_id": SAMRAD_SOURCE,
            "started_at": checked,
            "finished_at": checked,
            "status": "success",
            "scope_hash": scope_hash,
            "source_snapshot_at": checked,
            "records_seen": len(layer_features),
            "records_valid": len(layer_features),
            "records_rejected": 0,
            "snapshot_ref": snapshot_path,
            "checksum": f"sha256:{snapshot_digest}",
            "diagnostics": {
                "layer_counts": snapshot.get("counts") or {},
                "history_eligibility": "complete_for_configured_scope",
                "note": "Complete archived observation; absence is not interpreted as cancellation, deletion or completion.",
            },
        })

        for layer_name, feature in layer_features:
            props = feature.get("properties") or {}
            object_id = feature.get("id")
            if object_id in (None, ""):
                object_id = props.get("ObjectId")
            if object_id in (None, ""):
                object_id = props.get("OBJECTID")
            if object_id in (None, ""):
                raise ValueError(f"Samråd {layer_name}: feature without stable ObjectId in {snapshot_path}")
            object_id = str(object_id)
            source_record_id = f"{layer_name}:{object_id}"
            feature_hash = canonical_hash(feature)
            version_key = (source_record_id, feature_hash)
            observation_id = f"obs:{SAMRAD_SOURCE}:{source_record_id}:{feature_hash[:16]}"
            geometry_ref = (
                f"{snapshot_path}#/layers/{layer_name}/features/{object_id}/geometry"
                if feature.get("geometry") else None
            )
            if version_key not in seen_observation_versions:
                observations.append({
                    "observation_id": observation_id,
                    "source_id": SAMRAD_SOURCE,
                    "source_record_id": source_record_id,
                    "run_id": run_id,
                    "observed_at": checked,
                    "source_created_at": timestamp(props.get("Inkomdatum")),
                    "source_updated_at": None,
                    "valid_time": timestamp(props.get("Inkomdatum")),
                    "content_hash": f"sha256:{feature_hash}",
                    "raw_ref": f"{snapshot_path}#/layers/{layer_name}/features/{object_id}",
                    "geometry_ref": geometry_ref,
                    "geometry_crs": "EPSG:4326" if geometry_ref else None,
                    "quality_status": "valid",
                    "attributes": props,
                })
                seen_observation_versions.add(version_key)
            case_number = usable_case_number(props.get("Beteckn"))
            uuid = str(props.get("UUID") or "").strip()
            group_key = (
                f"case:{case_number.casefold()}" if case_number
                else f"uuid:{uuid.casefold()}" if uuid
                else f"feature:{source_record_id}"
            )
            cases.setdefault(group_key, []).append({
                "layer": layer_name, "feature": feature, "props": props,
                "observation_id": observation_id, "geometry": projected_area_geometry(feature.get("geometry")),
                "source_record_id": source_record_id, "observed_at": checked,
                "snapshot_path": snapshot_path, "run_id": run_id,
                "geometry_ref": geometry_ref, "feature_hash": feature_hash,
            })

    for group_key, all_rows in sorted(cases.items()):
        # Collapse duplicate unchanged versions while retaining distinct versions over time.
        unique_rows: dict[tuple[str, str], dict[str, Any]] = {}
        for row in all_rows:
            unique_rows.setdefault((row["source_record_id"], row["feature_hash"]), row)
        rows = sorted(unique_rows.values(), key=lambda row: (row["observed_at"], row["source_record_id"]))
        latest_time = max(row["observed_at"] for row in all_rows)
        latest_rows = [row for row in all_rows if row["observed_at"] == latest_time]
        latest_by_source = {row["source_record_id"]: row for row in latest_rows}
        current_rows = [latest_by_source[key] for key in sorted(latest_by_source)]
        primary = current_rows[0]
        props = primary["props"]
        case_number = usable_case_number(props.get("Beteckn"))
        uuid = props.get("UUID")
        event_id = f"samrad-case:{canonical_hash(group_key)[:20]}"
        event_observation_ids = sorted({row["observation_id"] for row in rows})
        first_seen = min(row["observed_at"] for row in all_rows)
        last_seen = max(row["observed_at"] for row in all_rows)
        dates = [date_value(row["props"].get("Inkomdatum")) for row in current_rows]
        dates = [value for value in dates if value is not None]
        event_date = min(dates) if dates else None
        event_date_iso = event_date.isoformat() + "T00:00:00Z" if event_date else None
        action = props.get("Samradsatgard") or "åtgärd ej angiven"
        status = props.get("Status") or "status ej angiven"
        municipality = props.get("Kommun") or "kommun ej angiven"
        events.append({
            "event_id": event_id,
            "event_type": "forest_consultation",
            "event_status": "registered_in_source",
            "title": f"Samråd {case_number or uuid or primary['source_record_id']}",
            "summary": (
                f"Skogsstyrelsens Samrådslager redovisar {action} i {municipality}. "
                f"Källstatus vid senaste observation: {status}. "
                "Historisk frånvaro i senare uttag tolkas inte som avslut, avbokning eller genomförd åtgärd."
            ),
            "event_time_start": event_date_iso,
            "event_time_end": None,
            "first_observed_at": first_seen,
            "last_observed_at": last_seen,
            "geometry_ref": primary["geometry_ref"],
            "confidence_class": "verified",
            "interpretation_version": "samrad-event-history-v2",
        })
        for index, observation_id in enumerate(event_observation_ids):
            evidence.append({
                "event_id": event_id,
                "observation_id": observation_id,
                "evidence_role": "primary" if index == 0 else "corroborating",
                "match_method": "same_samrad_case_key",
                "match_score": 100,
                "confidence_class": "verified",
                "reason_codes": ["samrad_case_grouped_by_beteckn_uuid_or_feature_id", "dated_snapshot_observation"],
                "review_status": "unreviewed",
            })
        geometries = [row["geometry"] for row in current_rows if row["geometry"] is not None]
        combined_geometry = unary_union(geometries) if geometries else None
        samrad_index.append({
            "event_id": event_id,
            "case_number": case_number,
            "date": event_date,
            "municipality": municipality_key(props),
            "geometry": combined_geometry,
            "observation_ids": event_observation_ids,
            "title": f"Samråd {case_number or uuid or primary['source_record_id']}",
        })
    return source_runs, observations, events, evidence, samrad_index

def build_bundle(
    latest: dict[str, Any],
    history: dict[str, Any] | None = None,
    samrad: dict[str, Any] | None = None,
    samrad_snapshots: list[tuple[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    checked_at = timestamp(latest.get("checked_at"))
    cuts = latest.get("cutting_notifications") or {}
    planned_features = cuts.get("features")
    if not checked_at or cuts.get("status") != "ok" or not isinstance(planned_features, list):
        raise ValueError("Latest planned-harvest source snapshot is not a successful, timestamped result.")

    area = latest.get("area") or {}
    planned_scope = {
        "source_url": cuts.get("url"),
        "area": {
            "latitude": area.get("latitude"),
            "longitude": area.get("longitude"),
            "radius_km": area.get("radius_km"),
        },
    }
    planned_scope_hash = canonical_hash(planned_scope)
    planned_run_id = f"{PLANNED_SOURCE}:{checked_at}:{planned_scope_hash[:12]}"
    cases = (history or {}).get("cases") or {}

    source_runs = [{
        "run_id": planned_run_id,
        "source_id": PLANNED_SOURCE,
        "started_at": checked_at,
        "finished_at": checked_at,
        "status": "success",
        "scope_hash": planned_scope_hash,
        "source_snapshot_at": None,
        "records_seen": len(planned_features),
        "records_valid": 0,
        "records_rejected": 0,
        "snapshot_ref": "data/latest.json#/cutting_notifications",
        "checksum": canonical_hash(planned_features),
        "diagnostics": {
            "area": area.get("name"),
            "query_url": cuts.get("url"),
            "note": "Successful current source result. This local area snapshot is not the national archive.",
        },
    }]

    observations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    chains: list[dict[str, Any]] = []
    planned_index: list[dict[str, Any]] = []
    seen_planned_ids: set[str] = set()

    for feature in sorted(planned_features, key=lambda item: str(item.get("id") or (item.get("properties") or {}).get("OBJECTID") or "")):
        props = feature.get("properties") or {}
        source_record_id = feature.get("id")
        if source_record_id in (None, ""):
            source_record_id = props.get("OBJECTID")
        if source_record_id in (None, ""):
            continue
        source_record_id = str(source_record_id)
        if source_record_id in seen_planned_ids:
            raise ValueError(f"Duplicate planned source record ID: {source_record_id}")
        seen_planned_ids.add(source_record_id)

        feature_hash = canonical_hash(feature)
        observation_id = f"obs:{PLANNED_SOURCE}:{source_record_id}:{feature_hash[:16]}"
        event_id = f"planned-harvest:{source_record_id}"
        chain_id = f"harvest-chain:{source_record_id}"
        case = cases.get(source_record_id) or {}
        first_seen = timestamp(case.get("first_seen_at")) or checked_at
        last_seen = timestamp(case.get("last_seen_at")) or checked_at
        received = timestamp(props.get("Inkomdatum"))
        geometry_ref = f"data/latest.json#/cutting_notifications/features/{source_record_id}/geometry" if feature.get("geometry") else None

        observations.append({
            "observation_id": observation_id,
            "source_id": PLANNED_SOURCE,
            "source_record_id": source_record_id,
            "run_id": planned_run_id,
            "observed_at": checked_at,
            "source_created_at": received,
            "source_updated_at": None,
            "valid_time": received,
            "content_hash": f"sha256:{feature_hash}",
            "raw_ref": f"data/latest.json#/cutting_notifications/features/{source_record_id}",
            "geometry_ref": geometry_ref,
            "geometry_crs": "EPSG:4326" if geometry_ref else None,
            "quality_status": "valid",
            "attributes": props,
        })

        case_number = props.get("Beteckn") or source_record_id
        municipality = props.get("Kommun") or "kommun ej angiven"
        source_status = props.get("ArendeStatus") or "status ej angiven"
        summary = (
            f"Skogsstyrelsen redovisar avverkningsanmälan {case_number} i {municipality}. "
            f"Källstatus: {source_status}. Detta är en registrerad anmälan, inte belägg för att avverkning har utförts."
        )
        events.append({
            "event_id": event_id,
            "event_type": "planned_harvest_notification",
            "event_status": "registered_in_source",
            "title": f"Avverkningsanmälan {case_number}",
            "summary": summary,
            "event_time_start": received,
            "event_time_end": None,
            "first_observed_at": first_seen,
            "last_observed_at": last_seen,
            "geometry_ref": geometry_ref,
            "confidence_class": "verified",
            "interpretation_version": INTERPRETATION_VERSION,
        })
        evidence.append({
            "event_id": event_id,
            "observation_id": observation_id,
            "evidence_role": "primary",
            "match_method": "same_source_record_id",
            "match_score": 100,
            "confidence_class": "verified",
            "reason_codes": ["source_record_exists", "same_source_record_id"],
            "review_status": "unreviewed",
        })
        chains.append({
            "chain_id": chain_id,
            "chain_type": "planned_harvest_follow_up",
            "primary_area_ref": f"observation:{observation_id}",
            "started_at": first_seen,
            "last_activity_at": last_seen,
            "chain_status": "open",
            "summary": f"Uppföljningskedja för avverkningsanmälan {case_number}.",
            "confidence_class": "verified",
            "event_ids": [event_id],
        })
        planned_index.append({
            "event_id": event_id,
            "chain_id": chain_id,
            "observation_id": observation_id,
            "case_number": usable_case_number(props.get("Beteckn")),
            "date": date_value(props.get("Inkomdatum")),
            "municipality": municipality_key(props),
            "geometry": projected_area_geometry(feature.get("geometry")),
        })

    if not observations:
        raise ValueError("No valid planned source records found; refusing to publish an empty event bundle.")
    source_runs[0]["records_valid"] = len(planned_index)
    source_runs[0]["records_rejected"] = len(planned_features) - len(planned_index)

    samrad_runs, samrad_observations, samrad_events, samrad_evidence, samrad_index = build_samrad_history(
        samrad_snapshots if samrad_snapshots else (
            [("data/samrad_latest.json", samrad)] if isinstance(samrad, dict) else []
        )
    )
    source_runs.extend(samrad_runs)
    observations.extend(samrad_observations)
    events.extend(samrad_events)
    evidence.extend(samrad_evidence)

    if samrad_index:
        chain_by_id = {chain["chain_id"]: chain for chain in chains}
        for planned in planned_index:
            candidates = []
            for samrad_case in samrad_index:
                exact_case = bool(
                    planned["case_number"] and samrad_case["case_number"]
                    and planned["case_number"].casefold() == samrad_case["case_number"].casefold()
                )
                overlap_ha = 0.0
                distance_m = None
                if planned["geometry"] is not None and samrad_case["geometry"] is not None:
                    distance_m = planned["geometry"].distance(samrad_case["geometry"])
                    if distance_m == 0:
                        overlap_ha = planned["geometry"].intersection(samrad_case["geometry"]).area / 10000
                if not exact_case and overlap_ha < 0.01 and (distance_m is None or distance_m > 30):
                    continue

                same_municipality = bool(
                    planned["municipality"] and samrad_case["municipality"]
                    and planned["municipality"] == samrad_case["municipality"]
                )
                day_gap = None
                if planned["date"] and samrad_case["date"]:
                    day_gap = abs((planned["date"] - samrad_case["date"]).days)
                score = 100 if exact_case else 0
                if overlap_ha >= 0.1:
                    score += 50
                elif overlap_ha >= 0.01:
                    score += 35
                elif distance_m is not None and distance_m <= 30:
                    score += 15
                if same_municipality:
                    score += 20
                if day_gap is not None and day_gap <= 365:
                    score += 20
                elif day_gap is not None and day_gap <= 730:
                    score += 10
                score = min(100, score)
                if exact_case:
                    confidence = "verified"
                elif overlap_ha >= 0.1 and same_municipality and day_gap is not None and day_gap <= 730:
                    confidence = "supported"
                else:
                    confidence = "indicative"
                relation_type = (
                    "possible_follow_up"
                    if samrad_case["date"] and planned["date"] and samrad_case["date"] <= planned["date"]
                    else "same_area"
                )
                candidates.append((score, confidence, relation_type, overlap_ha, distance_m, day_gap, same_municipality, samrad_case))

            candidates.sort(key=lambda row: (-row[0], row[7]["event_id"]))
            for score, confidence, relation_type, overlap_ha, distance_m, day_gap, same_municipality, samrad_case in candidates[:3]:
                method = "geometry_intersection_epsg3006" if overlap_ha >= 0.01 else "geometry_distance_epsg3006"
                if samrad_case["case_number"] and planned["case_number"] and samrad_case["case_number"].casefold() == planned["case_number"].casefold():
                    method = "exact_case_reference"
                relation_id = f"rel:{canonical_hash([planned['event_id'], samrad_case['event_id'], relation_type])[:20]}"
                relationships.append({
                    "relationship_id": relation_id,
                    "from_event_id": planned["event_id"],
                    "to_event_id": samrad_case["event_id"],
                    "relationship_type": relation_type,
                    "match_method": method,
                    "evidence_refs": [planned["observation_id"], *samrad_case["observation_ids"][:3]],
                    "confidence_class": confidence,
                    "rule_version": "harvest-samrad-link-v1",
                    "review_status": "needs_review" if confidence != "verified" else "unreviewed",
                })
                if confidence in {"verified", "supported"}:
                    chain = chain_by_id[planned["chain_id"]]
                    if samrad_case["event_id"] not in chain["event_ids"]:
                        chain["event_ids"].append(samrad_case["event_id"])
                    chain["confidence_class"] = "supported" if confidence == "supported" else "verified"
                    chain["summary"] += (
                        f" Möjlig samrådskoppling: {samrad_case['title']} "
                        f"(matchning {method}, cirka {overlap_ha:.2f} ha överlapp, "
                        f"kommunmatchning={same_municipality}, datumavstånd={day_gap} dagar). "
                        "Sambandet är analytiskt stöd, inte bevis för orsakssamband."
                    )

    generated_at = max([checked_at, *[row["started_at"] for row in source_runs]])
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "source_runs": source_runs,
        "observations": observations,
        "events": events,
        "evidence": evidence,
        "relationships": relationships,
        "chains": chains,
    }


def main() -> int:
    latest = load_json(LATEST)
    if not isinstance(latest, dict):
        print(f"ERROR: missing or invalid {LATEST}", file=sys.stderr)
        return 1
    history = load_json(HISTORY, {})
    samrad = load_json(SAMRAD, None)
    try:
        samrad_snapshots = load_samrad_snapshot_archive()
        bundle = build_bundle(
            latest,
            history if isinstance(history, dict) else {},
            samrad if isinstance(samrad, dict) else None,
            samrad_snapshots,
        )
        sys.path.insert(0, str(ROOT / "data-platform" / "scripts"))
        from validate_event_bundle import SCHEMA, validate_bundle
        schema = load_json(SCHEMA)
        errors = validate_bundle(bundle, schema)
        if errors:
            raise ValueError("Event bundle validation failed: " + "; ".join(errors[:10]))
    except (ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(OUT.suffix + ".tmp")
    temporary.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUT)
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "source_runs": len(bundle["source_runs"]),
        "source_observations": len(bundle["observations"]),
        "canonical_events": len(bundle["events"]),
        "event_chains": len(bundle["chains"]),
        "candidate_relationships": len(bundle["relationships"]),
        "samrad_archived_snapshots": len(samrad_snapshots),
        "samrad_observations": sum(1 for row in bundle["observations"] if row["source_id"] == SAMRAD_SOURCE),
        "satellite_indications_included": False,
        "schema_validation": "passed",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
