#!/usr/bin/env python3
"""Resumable Kungjort API ingestion directly into private Azure Blob Storage."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

BASE = "https://handlingar.kungjort.se/api/v1"
ACCOUNT_URL = "https://stskogkolldata.blob.core.windows.net"
STATE_CONTAINER = "metadata"
STATE_BLOB = "kungjort/state.json"
RAW_CONTAINER = "kungjort-raw"
CHANGES_CONTAINER = "kungjort-changes"
PAGE_SIZE = 100
USER_AGENT = "Skog-Kungjort-Azure/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cursor_key(cursor: str | None) -> str:
    return sha256_bytes((cursor if cursor is not None else "initial").encode("utf-8"))[:24]


def canonical_hash(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def initial_state() -> dict:
    return {
        "schema_version": 1,
        "bootstrap_complete": False,
        "bootstrap_cursor": None,
        "changes_cursor": None,
        "last_sync_at": None,
        "storage_backend": "azure-blob",
    }


class KungjortApi:
    def __init__(self, key: str, opener=None, sleep=time.sleep):
        if not key:
            raise RuntimeError("Missing KUNGJORT_API_KEY")
        self.key = key
        self.opener = opener or urllib.request.urlopen
        self.sleep = sleep

    def get(self, path: str, params: dict | None = None):
        url = BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        for attempt in range(7):
            req = urllib.request.Request(url, headers={
                "Authorization": "Bearer " + self.key,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            })
            try:
                with self.opener(req, timeout=90) as response:
                    payload = json.load(response)
                    return payload, response.headers.get("X-Request-ID")
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 503) or attempt == 6:
                    body = exc.read().decode("utf-8", "replace")[:500]
                    raise RuntimeError(
                        f"Kungjort API HTTP {exc.code}; "
                        f"request_id={exc.headers.get('X-Request-ID')}; body={body}"
                    ) from exc
                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = max(1, min(300, int(retry_after))) if retry_after else min(120, 2 ** attempt + random.random())
                except ValueError:
                    delay = min(120, 2 ** attempt + random.random())
                self.sleep(delay)
        raise RuntimeError("API retry loop exhausted")


class AzureArchive:
    def __init__(self, service: BlobServiceClient):
        self.service = service

    def load_state(self) -> dict:
        client = self.service.get_blob_client(container=STATE_CONTAINER, blob=STATE_BLOB)
        try:
            state = json.loads(client.download_blob().readall())
        except ResourceNotFoundError:
            return initial_state()
        if state.get("schema_version") != 1:
            raise RuntimeError("Unsupported Azure Kungjort state schema")
        if state.get("storage_backend") not in (None, "azure-blob"):
            raise RuntimeError("Checkpoint backend does not match Azure archive")
        return state

    def save_state(self, state: dict) -> None:
        state["last_sync_at"] = utc_now()
        state["storage_backend"] = "azure-blob"
        client = self.service.get_blob_client(container=STATE_CONTAINER, blob=STATE_BLOB)
        payload = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        client.upload_blob(
            payload,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )

    def exists_with_source_hash(self, container: str, blob_name: str, source_hash: str) -> bool:
        client = self.service.get_blob_client(container=container, blob=blob_name)
        try:
            props = client.get_blob_properties()
        except ResourceNotFoundError:
            return False
        actual = (props.metadata or {}).get("source_sha256")
        if actual != source_hash:
            raise RuntimeError(
                f"Existing Azure batch has different source hash; refusing overwrite: {container}/{blob_name}"
            )
        return True

    def upload_batch(self, container: str, blob_name: str, payload: bytes, source_hash: str) -> bool:
        client = self.service.get_blob_client(container=container, blob=blob_name)
        digest = sha256_bytes(payload)
        metadata = {"sha256": digest, "source_sha256": source_hash}
        try:
            client.upload_blob(
                payload,
                overwrite=False,
                metadata=metadata,
                content_settings=ContentSettings(content_type="application/gzip"),
            )
        except ResourceExistsError:
            if self.exists_with_source_hash(container, blob_name, source_hash):
                return False
            raise
        props = client.get_blob_properties()
        if (props.metadata or {}).get("sha256") != digest or (props.metadata or {}).get("source_sha256") != source_hash:
            raise RuntimeError(f"Post-upload integrity verification failed: {container}/{blob_name}")
        if props.size != len(payload):
            raise RuntimeError(f"Post-upload size verification failed: {container}/{blob_name}")
        return True



RELEVANCE_FIELDS = (
    "title", "rubrik", "subject", "amne", "ämne", "summary", "sammanfattning",
    "description", "beskrivning", "organ", "doc_type", "document_type",
    "case_title", "arende", "ärende", "keywords", "tags",
)

RELEVANCE_RULES = {
    "high": {
        "skog_och_skogsbruk": (
            "skogsbruk", "skogsfastighet", "skogsfastigheter", "skogsägare",
            "skogsagare", "skogsforvaltning", "skogsförvaltning", "skogsskötsel",
            "skogsskotsel", "skogsvård", "skogsvard", "skoglig", "avverkning",
            "avverkningsanmälan", "avverkningsanmalan", "avverkningsrätt",
            "avverkningsratt", "gallring", "föryngring", "fooryngring",
            "skogsföryngring", "skogsforyngring", "röjning", "rojning",
            "markberedning", "hygg", "kalhygge", "slutavverkning",
            "skogsbruksplan", "skogsbruksområde", "skogsbruksomrade",
            "skogsbilväg", "skogsbilvag", "skogs väg", "virkesupplag",
            "virkestransport", "virkesavlägg", "virkesavlagg", "virkesaffär",
            "virkesaffar", "rotpost", "rotskog", "skogsskada", "stormfälld",
            "stormfalld", "granbarkborre", "barkborre", "skogsdike",
            "skogsdikning", "dikning i skogsmark",
        ),
        "naturvard_och_skydd": (
            "naturvård", "naturvard", "naturvårdsområde", "naturvardsomrade",
            "naturreservat", "reservatsbildning", "reservatsföreskrift",
            "reservatsforeskrift", "biotopskydd", "biotopskyddsområde",
            "biotopskyddsomrade", "nyckelbiotop", "naturvärde", "naturvarde",
            "naturvärdesinventering", "naturvardesinventering", "naturvärdesobjekt",
            "naturvardesobjekt", "artskydd", "artskyddsförordningen",
            "artskyddsforordningen", "fridlysning", "fridlyst", "Natura 2000",
            "habitatdirektivet", "fågeldirektivet", "fageldirektivet",
            "skyddad art", "skyddsvärd", "skyddsvard", "hänsynsområde",
            "hansynsomrade", "ekologisk kompensation", "grön infrastruktur",
            "gron infrastruktur", "strandskydd", "strandskyddsdispens",
            "samråd enligt 12 kap", "12 kap. 6",
        ),
        "mark_och_planering": (
            "markanvändning", "markanvandning", "markfråga", "markfraga",
            "exploatering", "exploateringsområde", "exploateringsomrade",
            "exploateringsavtal", "detaljplan", "planprogram", "översiktsplan",
            "oversiktsplan", "områdesbestämmelse", "omradesbestammelse",
            "fastighetsreglering", "fastighetsbildning", "lantmäteriförrättning",
            "lantmateriforrattning", "markförvärv", "markforvarv",
            "markförsäljning", "markforsaljning", "markanvisning",
            "markupplåtelse", "markupplatelse", "arrende", "tomträtt",
            "tomtratt", "nyttjanderätt", "nyttjanderatt", "servitut",
            "gemensamhetsanläggning", "gemensamhetsanlaggning",
            "ledningsrätt", "ledningsratt", "fastighetsköp", "fastighetskop",
            "markköp", "markkop", "markbyte", "kommunal mark",
        ),
        "miljo_och_tillstand": (
            "miljöbalken", "miljobalken", "miljötillstånd", "miljotillstand",
            "miljöprövning", "miljoprovning", "miljökonsekvensbeskrivning",
            "miljokonsekvensbeskrivning", "miljöbedömning", "miljobedomning",
            "miljötillsyn", "miljotillsyn", "tillsyn enligt miljöbalken",
            "förorenad mark", "fororenad mark", "föroreningsskada",
            "fororeningsskada", "marksanering", "efterbehandling",
            "avhjälpandeåtgärd", "avhjalpandeatgard", "miljöfarlig verksamhet",
            "miljofarlig verksamhet", "anmälningspliktig verksamhet",
            "tillståndspliktig verksamhet", "tillstandspliktig verksamhet",
            "täkt", "bergtäkt", "bergtakt", "grustäkt", "grustakt",
            "torvtäkt", "torvtakt", "masshantering", "vattenverksamhet",
            "vattenuttag", "markavvattning", "dikesrensning",
            "miljörapport", "miljorapport", "MKB",
        ),
    },
    "medium": {
        "energi_och_infrastruktur": (
            "vindkraft", "vindkraftspark", "vindpark", "vindkraftverk",
            "solpark", "solcellspark", "solkraft", "solenergianläggning",
            "solenergianlaggning", "energipark", "energiproduktion",
            "kraftledning", "elledning", "regionnät", "regionnat",
            "stamnät", "stamnat", "elnät", "elnat", "nätkoncession",
            "natkoncession", "transformatorstation", "batterilager",
            "energilager", "vägplan", "vagplan", "vägombyggnad",
            "vagombyggnad", "vägprojekt", "vagprojekt", "skogsbilväg",
            "skogsbilvag", "järnväg", "jarnvag", "järnvägsplan",
            "jarnvagsplan", "infrastruktur", "hamn", "farled",
        ),
        "klimat_och_vatten": (
            "klimat", "klimatanpassning", "klimatrisk", "klimatåtgärd",
            "klimatatgard", "översvämning", "oversvamning", "skyfall",
            "dagvatten", "våtmark", "vatmark", "våtmarksrestaurering",
            "vatmarksrestaurering", "torv", "torvmark", "dikningsföretag",
            "dikningsforetag", "vattenförvaltning", "vattenforvaltning",
            "vattenförekomst", "vattenforekomst", "vattenskyddsområde",
            "vattenskyddsomrade", "grundvatten", "ytvatten", "vattenstatus",
            "flödesreglering", "flodesreglering", "erosion", "ras och skred",
        ),
        "brand_och_risk": (
            "naturbrand", "skogsbrand", "brandrisk", "brandförebyggande",
            "brandforebyggande", "brandskydd i skog", "brandberedskap",
            "brandbekämpning", "brandbekampning", "brandgata",
            "brandriskprognos", "skogsbrandsrisk",
        ),
    },
}


def _normalise(value: str) -> str:
    """Case- and accent-insensitive matching for Swedish metadata."""
    import unicodedata
    value = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", value).casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.split())


def classify_document(row: dict) -> dict:
    """Classify metadata recursively; never inspect opaque IDs or URLs."""
    chunks = []

    def collect(value, key=""):
        if isinstance(value, str):
            if key.casefold() not in {"id", "document_id", "url", "file_url", "download_url", "cursor"}:
                chunks.append(value)
        elif isinstance(value, dict):
            for child_key, child_value in value.items():
                collect(child_value, str(child_key))
        elif isinstance(value, list):
            for item in value:
                collect(item, key)

    collect(row)
    searchable = _normalise(" ".join(chunks))
    matches = []
    for priority in ("high", "medium"):
        for category, terms in RELEVANCE_RULES[priority].items():
            matched = [term for term in terms if _normalise(term) in searchable]
            if matched:
                matches.append({"priority": priority, "category": category, "terms": matched})
    if any(item["priority"] == "high" for item in matches):
        priority = "high"
    elif matches:
        priority = "medium"
    else:
        priority = "low"
    return {
        "priority": priority,
        "categories": sorted({item["category"] for item in matches}),
        "matched_terms": sorted({term for item in matches for term in item["terms"]}),
        "rule_version": "2026-11-04-v1",
    }


def document_id(row: dict):
    return row.get("id") or row.get("document_id")


def fetch_detail(api: KungjortApi, row: dict) -> dict:
    doc_id = document_id(row)
    if not doc_id:
        raise RuntimeError("Document list item has no id/document_id")
    encoded = urllib.parse.quote(str(doc_id), safe="")
    detail, request_id = api.get(f"/documents/{encoded}")
    returned_id = detail.get("id") or detail.get("document_id") if isinstance(detail, dict) else None
    if returned_id is not None and str(returned_id) != str(doc_id):
        raise RuntimeError(f"Document detail id mismatch for requested id {doc_id}")
    return {
        "record_type": "document",
        "document_id": str(doc_id),
        "captured_at": utc_now(),
        "list_record": row,
        "detail": detail,
        "request_id": request_id,
    }


def encode_jsonl_gzip(records: list[dict]) -> bytes:
    import io
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        for record in records:
            gz.write((json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
    return raw.getvalue()


def bootstrap(api: KungjortApi, archive: AzureArchive, state: dict, max_pages: int) -> dict:
    if state.get("bootstrap_complete"):
        print("Historical bootstrap already complete.")
        return state
    cursor = state.get("bootstrap_cursor")
    if cursor and not state.get("changes_cursor"):
        raise RuntimeError("Bootstrap cursor exists without the original changes_cursor; refusing unsafe resume")

    pages = 0
    total_details = 0
    uploaded = 0
    while pages < max_pages:
        cursor_before = cursor
        page, _ = api.get("/documents", {"limit": PAGE_SIZE, **({"cursor": cursor} if cursor else {})})
        if not isinstance(page.get("documents"), list):
            raise RuntimeError("/documents response has no documents array")
        rows = page["documents"]
        if not state.get("changes_cursor"):
            initial_changes = page.get("changes_cursor")
            if not initial_changes:
                raise RuntimeError("First /documents page omitted changes_cursor; refusing unsafe bootstrap")
            state["changes_cursor"] = initial_changes

        classified = [(row, classify_document(row)) for row in rows]
        metadata_records = [{
            "record_type": "document_index",
            "document_id": str(document_id(row)) if document_id(row) is not None else None,
            "indexed_at": utc_now(),
            "metadata": row,
            "relevance": classification,
        } for row, classification in classified]
        index_hash = canonical_hash(metadata_records)
        index_blob = f"kungjort/index/bootstrap-live/page-{cursor_key(cursor_before)}.jsonl.gz"
        if metadata_records:
            archive.upload_batch(STATE_CONTAINER, index_blob, encode_jsonl_gzip(metadata_records), index_hash)

        relevant_rows = [(row, classification) for row, classification in classified
                         if classification["priority"] in ("high", "medium")]
        detail_source = [{"id": document_id(row), "relevance": classification}
                         for row, classification in relevant_rows]
        source_hash = canonical_hash(detail_source)
        blob_name = f"bootstrap-live/page-{cursor_key(cursor_before)}.jsonl.gz"
        already_exists = archive.exists_with_source_hash(RAW_CONTAINER, blob_name, source_hash)
        if relevant_rows and not already_exists:
            records = []
            for row, classification in relevant_rows:
                record = fetch_detail(api, row)
                record["relevance"] = classification
                records.append(record)
            payload = encode_jsonl_gzip(records)
            if archive.upload_batch(RAW_CONTAINER, blob_name, payload, source_hash):
                uploaded += 1
            total_details += len(records)
        elif relevant_rows and already_exists:
            print(f"Existing verified relevant detail batch reused: {blob_name}")
        else:
            print(f"No high/medium documents on page; metadata index only: {index_blob}")

        cursor = page.get("next_cursor")
        state["bootstrap_cursor"] = cursor
        if not cursor:
            state["bootstrap_complete"] = True
        # Commit checkpoint only after the page archive is verified in Azure.
        archive.save_state(state)
        pages += 1
        print(f"Bootstrap page {pages}: list_rows={len(rows)}; next_cursor_present={bool(cursor)}; batch_uploaded={not already_exists}")
        if not cursor:
            break

    print(json.dumps({
        "mode": "bootstrap",
        "pages_this_run": pages,
        "details_fetched_this_run": total_details,
        "index_rows_processed_this_run": pages * PAGE_SIZE,
        "batches_uploaded_this_run": uploaded,
        "bootstrap_complete": state["bootstrap_complete"],
        "checkpoint_persisted": True,
    }, ensure_ascii=False))
    return state


def sync_changes(api: KungjortApi, archive: AzureArchive, state: dict, max_pages: int) -> dict:
    if not state.get("bootstrap_complete"):
        raise RuntimeError("Changes sync is blocked until historical bootstrap is complete")
    cursor = state.get("changes_cursor")
    if not cursor:
        raise RuntimeError("No saved changes_cursor; refusing to start changes sync")

    pages = 0
    uploaded = 0
    while pages < max_pages:
        cursor_before = cursor
        payload, _ = api.get("/changes", {"cursor": cursor, "limit": PAGE_SIZE})
        changes = payload.get("changes")
        if not isinstance(changes, list):
            raise RuntimeError("/changes response has no changes array")
        source_hash = canonical_hash(changes)
        blob_name = f"changes-live/page-{cursor_key(cursor_before)}.jsonl.gz"
        already_exists = archive.exists_with_source_hash(CHANGES_CONTAINER, blob_name, source_hash)

        if changes and not already_exists:
            records = []
            for change in changes:
                action = str(change.get("operation") or change.get("action") or change.get("type") or "").lower()
                doc_id = change.get("document_id") or change.get("id")
                if action in ("delete", "deleted", "tombstone"):
                    records.append({
                        "record_type": "tombstone",
                        "document_id": str(doc_id) if doc_id is not None else None,
                        "captured_at": utc_now(),
                        "change": change,
                    })
                elif action in ("upsert", "insert", "update", "updated", "created"):
                    row = change.get("document") if isinstance(change.get("document"), dict) else change
                    # Change events can contain only an ID. Fetch the changed
                    # version once so keyword filtering cannot miss a relevant update.
                    detail = fetch_detail(api, row)
                    detail_payload = detail.get("detail") if isinstance(detail.get("detail"), dict) else {}
                    classification = classify_document({**row, **detail_payload})
                    records.append({
                        "record_type": "document_index",
                        "document_id": str(document_id(row)) if document_id(row) is not None else None,
                        "captured_at": utc_now(),
                        "metadata": row,
                        "relevance": classification,
                    })
                    if classification["priority"] in ("high", "medium"):
                        detail["relevance"] = classification
                        records.append(detail)
                else:
                    raise RuntimeError(f"Unknown change operation {action!r}; refusing to advance cursor")
            if archive.upload_batch(CHANGES_CONTAINER, blob_name, encode_jsonl_gzip(records), source_hash):
                uploaded += 1
        elif changes and already_exists:
            print(f"Existing verified changes page reused: {blob_name}")

        next_cursor = payload.get("next_cursor") or payload.get("changes_cursor")
        if not next_cursor:
            if changes:
                raise RuntimeError("Non-empty /changes page omitted continuation cursor")
            break
        if next_cursor == cursor:
            raise RuntimeError("/changes cursor did not advance")
        cursor = next_cursor
        state["changes_cursor"] = cursor
        archive.save_state(state)
        pages += 1
        print(f"Changes page {pages}: changes={len(changes)}; batch_uploaded={bool(changes) and not already_exists}")
        if not payload.get("next_cursor"):
            break

    print(json.dumps({
        "mode": "changes",
        "pages_this_run": pages,
        "batches_uploaded_this_run": uploaded,
        "checkpoint_persisted": True,
    }, ensure_ascii=False))
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("bootstrap", "changes"), required=True)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--account-name", default="stskogkolldata")
    args = parser.parse_args()
    if args.max_pages < 1 or args.max_pages > 500:
        parser.error("--max-pages must be between 1 and 500")
    api = KungjortApi(os.environ.get("KUNGJORT_API_KEY"))
    credential = DefaultAzureCredential()
    service = BlobServiceClient(
        account_url=f"https://{args.account_name}.blob.core.windows.net",
        credential=credential,
    )
    try:
        archive = AzureArchive(service)
        state = archive.load_state()
        if args.mode == "bootstrap":
            bootstrap(api, archive, state, args.max_pages)
        else:
            sync_changes(api, archive, state, args.max_pages)
    finally:
        service.close()
        credential.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
