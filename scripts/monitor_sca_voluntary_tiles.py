#!/usr/bin/env python3
"""Incremental SCA voluntary MVT monitor. Tile-local hashes are not object IDs."""
from __future__ import annotations
import argparse, gzip, hashlib, json, os, threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import mapbox_vector_tile, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
LOCAL=threading.local()
TIMEOUT=(20,60)

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def key(z,x,y):
    return f"{z}/{x}/{y}"

def get_session():
    s=getattr(LOCAL,"session",None)
    if s is None:
        retry=Retry(total=4,connect=4,read=3,status=3,backoff_factor=1,
                    status_forcelist=[429,500,502,503,504],allowed_methods=["GET"],
                    respect_retry_after_header=True)
        s=requests.Session()
        s.headers.update({"User-Agent":"Skog-SCA-change-monitor/1.0",
                          "Accept":"application/vnd.mapbox-vector-tile, application/x-protobuf, */*"})
        s.mount("https://",HTTPAdapter(max_retries=retry,pool_connections=4,pool_maxsize=4))
        LOCAL.session=s
    return s

def feature_record(layer,f):
    geom=f.get("geometry") or {}
    props=f.get("properties") or {}
    return {"layer":layer,"feature_id":f.get("id"),"geometry":geom,
            "geometry_sha256":digest(geom),"properties":props,
            "properties_sha256":digest(props)}

def features_from_layers(layers):
    out=[]
    for layer in layers:
        out.extend(feature_record(layer.get("name","unknown"),f) for f in layer.get("features",[]))
    return sorted(out,key=lambda f:(f["layer"],f["geometry_sha256"],f["properties_sha256"]))

def baseline_record(row):
    return {"z":int(row["z"]),"x":int(row["x"]),"y":int(row["y"]),
            "url":row.get("url") or URL.format(z=row["z"],x=row["x"],y=row["y"]),
            "http_status":row.get("http_status"),"bytes":row.get("bytes",0),
            "sha256":row.get("sha256"),"state":row.get("state","unknown"),
            "features":features_from_layers(row.get("layers",[])),
            "pending_missing":[],"last_success_at":None,"not_found_streak":0,
            "covering_z9_seeds":row.get("covering_z9_seeds",[])}

def build_baseline(directory):
    files=sorted(directory.rglob("*.json"))
    if not files: raise ValueError(f"No baseline batch JSON files under {directory}")
    tiles={}
    for path in files:
        payload=json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("tile_results",[]):
            item=baseline_record(row); k=key(item["z"],item["x"],item["y"])
            if k in tiles and tiles[k].get("sha256")!=item.get("sha256"):
                raise ValueError(f"Conflicting baseline tile records: {k}")
            tiles[k]=item
    if not tiles: raise ValueError("Baseline artifacts contain no tiles")
    return {"schema_version":1,"source":URL,"baseline_type":"existing_z12_expansion_artifacts",
            "baseline_built_at":now(),"last_checked_at":None,"tile_count":len(tiles),
            "baseline_tile_count":len(tiles),"tiles":dict(sorted(tiles.items()))}

def read_state(path,baseline_dir):
    if path.exists():
        with gzip.open(path,"rt",encoding="utf-8") as f: return json.load(f)
    if baseline_dir is None: raise FileNotFoundError(f"No state {path}; provide --baseline-dir")
    return build_baseline(baseline_dir)

def write_baseline_archive(directory,path):
    """Persist the immutable first source snapshot once; later state stores hashes/metadata only."""
    if path.exists():
        return
    files=sorted(directory.rglob("*.json"))
    if not files:
        raise ValueError(f"No baseline batch JSON files under {directory}")
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw,mode="wb",mtime=0) as gz:
            for file in files:
                payload=json.loads(file.read_text(encoding="utf-8"))
                for row in payload.get("tile_results",[]):
                    for layer in row.get("layers",[]):
                        for feature in layer.get("features",[]):
                            item=feature_record(layer.get("name","unknown"),feature)
                            record={"baseline_run_id":41704577034,
                                    "tile":key(row["z"],row["x"],row["y"]),
                                    "source_url":row.get("url"),
                                    "source_tile_sha256":row.get("sha256"),
                                    **item}
                            gz.write((json.dumps(record,ensure_ascii=False,sort_keys=True)+"\n").encode())
    os.replace(tmp,path)

def write_state(path,state):
    # Keep the current index compact. Full baseline geometry lives in the immutable
    # baseline archive; new/changed geometries live in append-only event archives.
    compact=dict(state)
    compact_tiles={}
    def without_geometry(feature):
        return {k:v for k,v in feature.items() if k!="geometry"}
    for tile_id,tile in state["tiles"].items():
        item=dict(tile)
        item["features"]=[without_geometry(f) for f in tile.get("features",[])]
        item["pending_missing"]=[{**entry,"feature":without_geometry(entry["feature"])}
                                 for entry in tile.get("pending_missing",[])]
        compact_tiles[tile_id]=item
    compact["tiles"]=compact_tiles
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw,mode="wb",mtime=0) as gz:
            gz.write(json.dumps(compact,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode())
    os.replace(tmp,path)

def fetch(z,x,y,previous_sha=None,previous_state=None):
    url=URL.format(z=z,x=x,y=y)
    try:
        r=get_session().get(url,timeout=TIMEOUT); raw=r.content
        base={"z":z,"x":x,"y":y,"url":url,"http_status":r.status_code,
              "bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest() if raw else None,
              "content_type":r.headers.get("Content-Type"),"server":r.headers.get("Server")}
        if r.status_code==404: return {**base,"state":"not_found_404","features":[],"body_preview":raw[:240].decode("utf-8",errors="replace")}
        if r.status_code!=200: return {**base,"state":"http_error","features":[],"error":f"HTTP {r.status_code}","body_preview":raw[:240].decode("utf-8",errors="replace")}
        if digest_value:=base["sha256"]:
            if digest_value==previous_sha and str(previous_state or "").startswith("valid_mvt"):
                return {**base,"state":"unchanged"}
        try:
            decoded=mapbox_vector_tile.decode(raw)
            layers=[{"name":n,"features":v.get("features",[])} for n,v in decoded.items()]
            feats=features_from_layers(layers)
            return {**base,"state":"valid_mvt_with_features" if feats else "valid_mvt_empty","features":feats}
        except Exception as e: return {**base,"state":"decode_error","features":[],"error":str(e)[:240]}
    except Exception as e:
        return {"z":z,"x":x,"y":y,"url":url,"state":"request_error","features":[],"error":str(e)[:240]}

def fkey(f):
    return f["layer"],f["geometry_sha256"],f["properties_sha256"]

def compare_features(tile_id,old,new,at):
    old_active=list(old.get("features",[])); old_pending=list(old.get("pending_missing",[]))
    new_features=list(new.get("features",[])); old_pool=old_active+[x["feature"] for x in old_pending]
    ob=defaultdict(list); nb=defaultdict(list)
    for f in old_pool: ob[fkey(f)].append(f)
    for f in new_features: nb[fkey(f)].append(f)
    matched_old=set(); matched_new=set()
    for k in set(ob)&set(nb):
        n=min(len(ob[k]),len(nb[k]))
        matched_old.update(id(x) for x in ob[k][:n]); matched_new.update(id(x) for x in nb[k][:n])
    ou=[x for x in old_pool if id(x) not in matched_old]
    nu=[x for x in new_features if id(x) not in matched_new]
    events=[]
    # Same geometry, changed attributes.
    og=defaultdict(list); ng=defaultdict(list)
    for f in ou: og[(f["layer"],f["geometry_sha256"])].append(f)
    for f in nu: ng[(f["layer"],f["geometry_sha256"])].append(f)
    for k in set(og)&set(ng):
        while og[k] and ng[k]:
            a,b=og[k].pop(),ng[k].pop()
            events.append({"event_type":"metadata_changed","tile":tile_id,"layer":b["layer"],
                           "geometry_sha256":b["geometry_sha256"],"old_properties":a["properties"],
                           "new_properties":b["properties"],"observed_at":at})
            ou.remove(a); nu.remove(b)
    # Same properties, changed geometry: candidate only.
    op=defaultdict(list); np=defaultdict(list)
    for f in ou: op[(f["layer"],f["properties_sha256"])].append(f)
    for f in nu: np[(f["layer"],f["properties_sha256"])].append(f)
    for k in set(op)&set(np):
        if len(op[k])==len(np[k])==1:
            a,b=op[k][0],np[k][0]
            events.append({"event_type":"geometry_changed_candidate","tile":tile_id,"layer":b["layer"],
                           "old_geometry_sha256":a["geometry_sha256"],
                           "new_geometry":b["geometry"],"new_geometry_sha256":b["geometry_sha256"],
                           "properties":b["properties"],"observed_at":at,"identity_resolved":False})
            ou.remove(a); nu.remove(b)
    pending=[]
    for item in old_pending:
        f=item["feature"]
        if f in ou:
            count=int(item.get("missing_count",1))+1
            if count>=2:
                events.append({"event_type":"geometry_removed_confirmed","tile":tile_id,"layer":f["layer"],
                               "geometry_sha256":f["geometry_sha256"],
                               **({"geometry":f["geometry"]} if f.get("geometry") is not None else {}),
                               "properties":f["properties"],"first_missing_at":item.get("first_missing_at"),
                               "confirmed_at":at})
            else: pending.append({**item,"missing_count":count})
            ou.remove(f)
    for f in ou:
        pending.append({"feature":f,"missing_count":1,"first_missing_at":at})
        events.append({"event_type":"geometry_missing_candidate","tile":tile_id,"layer":f["layer"],
                       "geometry_sha256":f["geometry_sha256"],
                       **({"geometry":f["geometry"]} if f.get("geometry") is not None else {}),
                       "properties":f["properties"],"observed_at":at,"confirmation_required":True})
    for f in nu:
        events.append({"event_type":"geometry_added","tile":tile_id,"layer":f["layer"],
                       "geometry":f["geometry"],"geometry_sha256":f["geometry_sha256"],
                       "properties":f["properties"],"properties_sha256":f["properties_sha256"],
                       "observed_at":at})
    return events,new_features,pending

def apply_result(old,new,at):
    tid=key(new["z"],new["x"],new["y"])
    if new["state"] in ("request_error","http_error","decode_error"):
        kept=dict(old); kept.update({"last_attempt_at":at,"last_attempt_state":new["state"],
                                     "last_error":new.get("error"),"last_attempt_http_status":new.get("http_status"),
                                     "last_attempt_sha256":new.get("sha256"),"last_attempt_bytes":new.get("bytes"),
                                     "last_attempt_content_type":new.get("content_type"),
                                     "last_attempt_body_preview":new.get("body_preview")})
        return kept,[{"event_type":"tile_poll_error","tile":tid,"state":new["state"],
                      "error":new.get("error"),"observed_at":at}]
    if new["state"]=="not_found_404":
        # Sparse tile delivery: 404 is unavailable, never evidence that features
        # disappeared. Do not increment feature missing counters or delete data.
        kept=dict(old); streak=int(old.get("not_found_streak",0))+1
        kept.update({"not_found_streak":streak,"last_attempt_at":at,"last_attempt_state":"not_found_404",
                     "last_attempt_http_status":new.get("http_status",404),
                     "last_attempt_sha256":new.get("sha256"),"last_attempt_bytes":new.get("bytes"),
                     "last_attempt_content_type":new.get("content_type"),
                     "last_attempt_body_preview":new.get("body_preview")})
        ev=[]
        if streak==2 and old.get("features"):
            ev.append({"event_type":"tile_unavailable_candidate","tile":tid,"observed_at":at,
                       "note":"404 observed twice; old feature data retained; not a geometry removal"})
        return kept,ev
    if old.get("sha256")==new.get("sha256") and old.get("state","").startswith("valid_mvt"):
        ev=[]; pending=[]
        for item in old.get("pending_missing",[]):
            n=int(item.get("missing_count",1))+1; f=item["feature"]
            if n>=2:
                ev.append({"event_type":"geometry_removed_confirmed","tile":tid,"layer":f["layer"],
                           "geometry_sha256":f["geometry_sha256"],
                           **({"geometry":f["geometry"]} if f.get("geometry") is not None else {}),
                           "properties":f["properties"],"first_missing_at":item.get("first_missing_at"),
                           "confirmed_at":at})
            else: pending.append({**item,"missing_count":n})
        kept=dict(old); kept.update({"pending_missing":pending,"last_success_at":at,
                                     "last_attempt_at":at,"last_attempt_state":new["state"],
                                     "not_found_streak":0})
        return kept,ev
    ev,active,pending=compare_features(tid,old,new,at)
    updated={**old,**new,"features":active,"pending_missing":pending,"last_success_at":at,
             "last_attempt_at":at,"last_attempt_state":new["state"],"not_found_streak":0}
    return updated,ev


def extend_tile_plan(state,census_path,coverage_audit_path=None):
    """Expand, never shrink, z12 monitoring from positive z9 and sampled z10-z12 tiles."""
    census=json.loads(census_path.read_text(encoding="utf-8"))
    rows=census.get("tile_results",[])
    summary=census.get("summary",{})
    expected=int(summary.get("tiles_in_bbox") or 0)
    completed=int(summary.get("tiles_completed") or 0)
    if not rows or expected<=0 or completed!=expected or len(rows)!=expected:
        raise ValueError("National z9 seed census incomplete; refusing to alter tile plan")
    allowed={"valid_mvt_with_features","valid_mvt_empty","not_found_404","http_error","request_error","decode_error"}
    voluntary_states=Counter()
    ownership_states=Counter()
    for row in rows:
        vol=row.get("voluntary",{}).get("state","pending")
        own=row.get("ownership",{}).get("state","pending")
        if vol not in allowed or own not in allowed:
            raise ValueError("National z9 seed census contains pending or unknown tile states; refusing to alter tile plan")
        voluntary_states[vol]+=1
        ownership_states[own]+=1

    discoveries=[]
    for row in rows:
        if row.get("voluntary",{}).get("state")=="valid_mvt_with_features":
            discoveries.append({"z":9,"x":int(row["x"]),"y":int(row["y"]),"source":"z9_census"})
    audit_summary={}
    audit_states={}
    if coverage_audit_path and coverage_audit_path.exists():
        audit=json.loads(coverage_audit_path.read_text(encoding="utf-8"))
        if audit.get("schema_version")!=1 or not audit.get("probe_results"):
            raise ValueError("Multi-zoom coverage audit missing or invalid; refusing to alter tile plan")
        audit_summary={k:audit.get(k) for k in ("samples_per_class_requested","unique_probe_tiles","probe_requests")}
        audit_states=audit.get("states_by_zoom",{})
        seen={(d["z"],d["x"],d["y"]) for d in discoveries}
        for row in audit["probe_results"]:
            z=int(row.get("z",0))
            if z in (10,11,12) and row.get("state")=="valid_mvt_with_features":
                ident=(z,int(row["x"]),int(row["y"]))
                if ident not in seen:
                    discoveries.append({"z":z,"x":ident[1],"y":ident[2],"source":"multizoom_audit"})
                    seen.add(ident)

    targets=defaultdict(set)
    for d in discoveries:
        z,x,y=d["z"],d["x"],d["y"]
        factor=2**(12-z)
        for dx in range(factor):
            for dy in range(factor):
                x0,y0=x*factor+dx,y*factor+dy
                for ox in range(-1,2):
                    for oy in range(-1,2):
                        tx,ty=x0+ox,y0+oy
                        if 0<=tx<4096 and 0<=ty<4096:
                            targets[(tx,ty)].add((z,x,y,d["source"]))
    added=0
    for (x,y),sources in targets.items():
        tile_id=key(12,x,y)
        if tile_id not in state["tiles"]:
            state["tiles"][tile_id]={"z":12,"x":x,"y":y,"url":URL.format(z=12,x=x,y=y),
                "http_status":None,"bytes":0,"sha256":None,"state":"unseen","features":[],
                "pending_missing":[],"last_success_at":None,"not_found_streak":0}
            added+=1
        tile=state["tiles"][tile_id]
        existing={(int(s["z"]),int(s["x"]),int(s["y"]),s.get("source","z9_census"))
                   for s in tile.get("discovery_sources",[])}
        existing.update(sources)
        tile["discovery_sources"]=[{"z":z,"x":sx,"y":sy,"source":source}
                                   for z,sx,sy,source in sorted(existing)]
        if any(z==9 for z,_,_,_ in sources):
            old={(int(s["x"]),int(s["y"])) for s in tile.get("covering_z9_seeds",[])}
            old.update((sx,sy) for z,sx,sy,_ in sources if z==9)
            tile["covering_z9_seeds"]=[{"z":9,"x":sx,"y":sy} for sx,sy in sorted(old)]

    state["tile_count"]=len(state["tiles"])
    state["latest_seed_census"]={
        "observed_at":now(),"tiles_in_bbox":expected,"tiles_completed":completed,
        "positive_voluntary_z9_tiles":sum(1 for r in rows if r.get("voluntary",{}).get("state")=="valid_mvt_with_features"),
        "positive_discovery_tiles_by_zoom":dict(Counter(str(d["z"]) for d in discoveries)),
        "positive_seed_tiles":discoveries,
        "voluntary_states":dict(voluntary_states),"ownership_states":dict(ownership_states),
        "voluntary_unknown_tiles":sum(voluntary_states[s] for s in ("not_found_404","http_error","request_error","decode_error")),
        "ownership_unknown_tiles":sum(ownership_states[s] for s in ("not_found_404","http_error","request_error","decode_error")),
        "multizoom_audit":audit_summary,"multizoom_states_by_zoom":audit_states
    }
    return added,len(discoveries)


def normalize_event(event):
    """Wrap a source event in a versioned, addressable feed envelope."""
    item=dict(event)
    tile=item.get("tile")
    zxy=None
    if tile:
        try:
            z,x,y=(int(v) for v in tile.split("/"))
            zxy={"z":z,"x":x,"y":y}
        except (ValueError,TypeError):
            zxy=None
    event_type=item.get("event_type","unknown")
    categories={"geometry_added":"geometry","geometry_changed_candidate":"geometry_candidate",
        "metadata_changed":"metadata","geometry_missing_candidate":"availability_candidate",
        "geometry_removed_confirmed":"availability_confirmed","tile_unavailable_candidate":"source_availability",
        "tile_poll_error":"technical"}
    eligible=event_type in {"geometry_added","metadata_changed","geometry_removed_confirmed"}
    identity={"event_type":event_type,"tile":tile,"layer":item.get("layer"),
        "geometry_sha256":item.get("geometry_sha256") or item.get("new_geometry_sha256"),
        "observed_at":item.get("observed_at") or item.get("confirmed_at"),
        "properties_sha256":item.get("properties_sha256") or digest(item.get("new_properties",item.get("properties",{})))}
    item.update({"event_schema_version":1,
        "event_id":hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "source_system":"sca_olga_mvt","source_tile":zxy,
        "source_url":URL.format(**zxy) if zxy else None,
        "event_category":categories.get(event_type,"other"),
        "notification_candidate":eligible,
        "identity_resolved":bool(item.get("identity_resolved",False))})
    return item

def run(state,workers):
    at=now(); tiles=state["tiles"]; fetched={}; errs=0
    coords=[(k,int(v["z"]),int(v["x"]),int(v["y"])) for k,v in tiles.items()]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(fetch,z,x,y,tiles[k].get("sha256"),tiles[k].get("state")):k for k,z,x,y in coords}
        for i,future in enumerate(as_completed(futures),1):
            k=futures[future]; fetched[k]=future.result()
            if fetched[k]["state"] in ("request_error","http_error","decode_error"): errs+=1
            if i%250==0 or i==len(futures):
                print(json.dumps({"progress":i,"total":len(futures),"errors":errs}),flush=True)
    events=[]; states=Counter(); nfeatures=0
    for k in sorted(tiles):
        tiles[k],ev=apply_result(tiles[k],fetched[k],at)
        events.extend(ev); states[fetched[k]["state"]]+=1; nfeatures+=len(fetched[k].get("features",[]))
    state["tiles"]=dict(sorted(tiles.items())); state["last_checked_at"]=at
    summary={"observed_at":at,"tiles_checked":len(tiles),"tile_states":dict(states),
             "feature_records_decoded":nfeatures,"unchanged_tiles":states.get("unchanged",0),"event_counts":dict(Counter(e["event_type"] for e in events)),
             "events":len(events),"poll_errors":errs,"identity_resolved":0}
    return state,events,summary

def write_events(path,events):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw,mode="wb",mtime=0) as gz:
            for e in events: gz.write((json.dumps(normalize_event(e),ensure_ascii=False,sort_keys=True)+"\n").encode())

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--state",type=Path,default=Path("data/sca/monitoring/tile-state.json.gz"))
    p.add_argument("--baseline-dir",type=Path)
    p.add_argument("--seed-census",type=Path)
    p.add_argument("--coverage-audit",type=Path)
    p.add_argument("--events",type=Path,default=Path("output/sca-voluntary-change-events.jsonl.gz"))
    p.add_argument("--summary",type=Path,default=Path("output/sca-voluntary-change-summary.json"))
    p.add_argument("--workers",type=int,default=3)
    a=p.parse_args()
    state=read_state(a.state,a.baseline_dir); bootstrap=state.get("last_checked_at") is None
    new_tiles_added=0; positive_seed_tiles=None
    if a.seed_census:
        new_tiles_added,positive_seed_tiles=extend_tile_plan(state,a.seed_census,a.coverage_audit)
    if bootstrap and a.baseline_dir:
        write_baseline_archive(a.baseline_dir,Path("data/sca/monitoring/baseline/source-features.jsonl.gz"))
    state,events,summary=run(state,max(1,min(6,a.workers)))
    summary.update({"bootstrapped_from_baseline":bootstrap,
                    "baseline_tile_count":state.get("baseline_tile_count",state["tile_count"]),
                    "tile_plan_tile_count":state["tile_count"],
                    "new_tiles_added_from_z9":new_tiles_added,
                    "positive_discovery_tiles":positive_seed_tiles,
                    "state_schema_version":state["schema_version"]})
    write_state(a.state,state); write_events(a.events,events)
    a.summary.parent.mkdir(parents=True,exist_ok=True)
    a.summary.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
