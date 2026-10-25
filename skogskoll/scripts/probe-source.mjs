import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";

const SERVICE = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer";
const ENDPOINT = SERVICE + "/0";
const OUT = "skogskoll/reports/source-probe-latest.json";
const PAGE_SIZE = 100;
const MAX_PAGES = 3;
const requestedFields = ["Beteckn", "Kommun", "Inkomdatum", "ArendeStatus", "AnmaldHa"];

async function getJson(url) {
  const response = await fetch(url, { headers: { "user-agent": "Skogskoll-source-probe/0.1 (read-only)" } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(`HTTP ${response.status} from ${url}`);
  if (!body) throw new Error("Invalid JSON response");
  if (body.error) throw new Error(body.error.message || JSON.stringify(body.error));
  return body;
}
function hash(value) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}
function stableId(feature, objectIdField = "OBJECTID") {
  const props = feature?.properties ?? {};
  return feature?.id ?? props[objectIdField] ?? props.OBJECTID ?? props.ObjectId ?? props.objectid ?? null;
}

const report = {
  checked_at: new Date().toISOString(),
  service: SERVICE,
  layer_endpoint: ENDPOINT,
  mode: "read-only; no alerts; no database writes",
  checks: {},
  errors: [],
};
try {
  const [service, layer, countResult] = await Promise.all([
    getJson(SERVICE + "?f=pjson"),
    getJson(ENDPOINT + "?f=pjson"),
    getJson(ENDPOINT + "/query?" + new URLSearchParams({
      where: "1=1", returnCountOnly: "true", f: "json"
    }))
  ]);
  if (!Number.isInteger(countResult.count)) throw new Error("Source did not return a valid total record count");
  const objectIdField = layer.objectIdField ?? (layer.fields ?? []).find(f => f.type === "esriFieldTypeOID")?.name;
  if (!objectIdField) throw new Error("No object ID field found in layer metadata");
  const validFields = new Set((layer.fields ?? []).map(f => f.name));
  const outFields = [objectIdField, ...requestedFields.filter(name => validFields.has(name))].join(",");
  const queryPage = offset => getJson(ENDPOINT + "/query?" + new URLSearchParams({
    where: "1=1", outFields, returnGeometry: "true", outSR: "4326", f: "geojson",
    resultRecordCount: String(PAGE_SIZE), orderByFields: `${objectIdField} ASC`, resultOffset: String(offset)
  }));
  const first = await queryPage(0);
  let newestSample = null;
  if (validFields.has("Inkomdatum")) {
    newestSample = await getJson(ENDPOINT + "/query?" + new URLSearchParams({
      where: "Inkomdatum IS NOT NULL", outFields, returnGeometry: "false", outSR: "4326", f: "geojson",
      resultRecordCount: String(PAGE_SIZE), orderByFields: `Inkomdatum DESC, ${objectIdField} DESC`, resultOffset: "0"
    }));
    if (!Array.isArray(newestSample.features)) throw new Error("Newest-record query did not return features array");
    const newestDates = newestSample.features.map(f => f.properties?.Inkomdatum)
      .filter(v => typeof v === "number" && Number.isFinite(v));
    report.checks.newest_records = {
      ok: true,
      count: newestSample.features.length,
      sample_ids: newestSample.features.slice(0, 10).map(f => stableId(f, objectIdField)),
      max_source_date: newestDates.length ? new Date(Math.max(...newestDates)).toISOString() : null,
      min_source_date_in_sample: newestDates.length ? new Date(Math.min(...newestDates)).toISOString() : null,
      status_values: [...new Set(newestSample.features.map(f => f.properties?.ArendeStatus).filter(v => v != null))],
      note: "Ordered by Inkomdatum descending. This is a recent-date sample, not confirmation that Inkomdatum means publication or notification date."
    };
  }
  report.checks.source_size = {
    ok: true,
    total_feature_count: countResult.count,
    sample_coverage: countResult.count ? first.features.length / countResult.count : null,
    note: "Count is from the service query API; the probe reads only a bounded sample, not all features."
  };
  report.checks.service_metadata = {
    ok: !service.error, service_name: service.name ?? null,
    currentVersion: service.currentVersion ?? null,
    layer_count: Array.isArray(service.layers) ? service.layers.length : null
  };
  report.checks.layer_metadata = {
    ok: !layer.error, name: layer.name ?? null, objectIdField: objectIdField,
    geometryType: layer.geometryType ?? null, maxRecordCount: layer.maxRecordCount ?? null,
    fields: (layer.fields ?? []).map(f => ({ name: f.name, type: f.type, alias: f.alias }))
  };
  if (!Array.isArray(first.features)) throw new Error("Query did not return a GeoJSON features array");
  report.checks.first_page = {
    ok: true, count: first.features.length,
    response_type: first.type ?? null,
    has_exceededTransferLimit: Boolean(first.exceededTransferLimit),
    sample_ids: first.features.slice(0, 10).map(f => stableId(f, objectIdField)),
    sample_properties: first.features.slice(0, 3).map(f => f.properties),
    geometry_types: [...new Set(first.features.map(f => f.geometry?.type ?? "null"))],
    stable_id_coverage: first.features.length
      ? first.features.filter(f => stableId(f, objectIdField) !== null).length / first.features.length : null
  };
  const pages = [first];
  let offset = first.features.length;
  for (let i = 1; i < MAX_PAGES && (first.exceededTransferLimit || first.features.length === PAGE_SIZE); i++) {
    const page = await queryPage(offset);
    if (!Array.isArray(page.features)) throw new Error("Paged query did not return features array");
    pages.push(page);
    offset += page.features.length;
    if (!page.features.length) break;
  }
  const all = pages.flatMap(p => p.features);
  const ids = all.map(f => stableId(f, objectIdField)).filter(v => v !== null).map(String);
  report.checks.pagination = {
    pages_checked: pages.length, fetched_count: all.length,
    unique_ids: new Set(ids).size, duplicate_ids: ids.length - new Set(ids).size,
    ids_monotonic_in_sample: ids.every((v, i) => i === 0 || Number(v) >= Number(ids[i - 1])),
    capped: pages.length === MAX_PAGES && Boolean(pages.at(-1)?.exceededTransferLimit)
  };
  const canonical = first.features.slice(0, 20).map(f => ({
    id: stableId(f, objectIdField), properties: f.properties, geometry_type: f.geometry?.type ?? null
  }));
  report.checks.repeatability_fingerprint = {
    sample_size: canonical.length,
    sha256: hash(canonical),
    note: "Compare this fingerprint across separate runs; it is a diagnostic, not proof of source immutability."
  };
  const businessKeys = first.features.map(f => f.properties?.Beteckn).filter(v => v !== null && v !== undefined && String(v).trim() !== "").map(String);
  const uniqueBusinessKeys = new Set(businessKeys);
  const dates = first.features.map(f => f.properties?.Inkomdatum).filter(v => typeof v === "number" && Number.isFinite(v));
  report.checks.field_semantics = {
    date_field_candidates: ["Inkomdatum"].filter(name =>
      (layer.fields ?? []).some(f => f.name === name)),
    status_field_candidates: ["ArendeStatus"].filter(name =>
      (layer.fields ?? []).some(f => f.name === name)),
    id_field_detected: objectIdField,
    business_key_field: (layer.fields ?? []).some(f => f.name === "Beteckn") ? "Beteckn" : null,
    sample_business_key_coverage: first.features.length ? businessKeys.length / first.features.length : null,
    sample_business_key_duplicates: businessKeys.length - uniqueBusinessKeys.size,
    sample_date_min: dates.length ? new Date(Math.min(...dates)).toISOString() : null,
    sample_date_max: dates.length ? new Date(Math.max(...dates)).toISOString() : null,
    note: "OBJECTID is the technical row ID; evaluate whether Beteckn is a stable case identifier before choosing production identity. Confirm Inkomdatum semantics before user-facing wording."
  };
  report.checks.scope = {
    requested_pages_limit: MAX_PAGES,
    page_size: PAGE_SIZE,
    intentionally_bounded_sample: true,
    note: "This probe validates source behavior on a bounded sample; it is not a full ingestion or completeness scan."
  };
  report.summary = "Probe completed on a bounded sample. This is not approval to activate alerts; repeat across a six-hour interval and verify stable IDs, pagination and field semantics before ingestion.";
} catch (error) {
  report.summary = "Probe failed; alerting must remain disabled.";
  report.errors.push(String(error?.stack ?? error));
  process.exitCode = 1;
}
await mkdir("skogskoll/reports", { recursive: true });
await writeFile(OUT, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
