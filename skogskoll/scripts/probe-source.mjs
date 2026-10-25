import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";

const SERVICE = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer";
const ENDPOINT = SERVICE + "/0";
const OUT = "skogskoll/reports/source-probe-latest.json";
const PAGE_SIZE = 100;
const MAX_PAGES = 3;
const requestedFields = ["Beteckn", "Kommun", "Inkomdatum", "ArendeStatus", "AnmaldHa"];

async function getJson(url) {
  const response = await fetch(url, { headers: { "user-agent": "Skogskoll-source-probe/0.3 (read-only)" } });
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
function sourceDate(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
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
  if (!Number.isInteger(countResult.count) || countResult.count < 0) {
    throw new Error("Source did not return a valid total record count");
  }

  const objectIdField = layer.objectIdField ?? (layer.fields ?? []).find(f => f.type === "esriFieldTypeOID")?.name;
  if (!objectIdField) throw new Error("No object ID field found in layer metadata");
  const validFields = new Set((layer.fields ?? []).map(f => f.name));
  const outFields = [objectIdField, ...requestedFields.filter(name => validFields.has(name))].join(",");
  const queryPage = offset => getJson(ENDPOINT + "/query?" + new URLSearchParams({
    where: "1=1", outFields, returnGeometry: "true", outSR: "4326", f: "geojson",
    resultRecordCount: String(PAGE_SIZE), orderByFields: `${objectIdField} ASC`, resultOffset: String(offset)
  }));

  const first = await queryPage(0);
  if (!Array.isArray(first.features)) throw new Error("Query did not return a GeoJSON features array");

  const newestSample = validFields.has("Inkomdatum")
    ? await getJson(ENDPOINT + "/query?" + new URLSearchParams({
        where: "Inkomdatum IS NOT NULL", outFields, returnGeometry: "false", outSR: "4326", f: "geojson",
        resultRecordCount: String(PAGE_SIZE), orderByFields: `Inkomdatum DESC, ${objectIdField} DESC`, resultOffset: "0"
      }))
    : null;
  if (newestSample && !Array.isArray(newestSample.features)) {
    throw new Error("Newest-record query did not return features array");
  }
  if (newestSample) {
    const dates = newestSample.features.map(f => f.properties?.Inkomdatum)
      .filter(v => typeof v === "number" && Number.isFinite(v));
    report.checks.newest_records = {
      ok: true,
      count: newestSample.features.length,
      sample_ids: newestSample.features.slice(0, 10).map(f => stableId(f, objectIdField)),
      max_source_date: dates.length ? sourceDate(Math.max(...dates)) : null,
      min_source_date_in_sample: dates.length ? sourceDate(Math.min(...dates)) : null,
      status_values: [...new Set(newestSample.features.map(f => f.properties?.ArendeStatus).filter(v => v != null))],
      note: "Ordered by Inkomdatum descending. This is a recent-date sample, not a publication timestamp or a first-observed timestamp."
    };
  }

  report.checks.source_size = {
    ok: true,
    total_feature_count: countResult.count,
    first_page_size: first.features.length,
    bounded_sample_coverage: countResult.count ? first.features.length / countResult.count : null,
    note: "The service count estimates current layer size; the probe intentionally reads only a bounded sample."
  };
  report.checks.service_metadata = {
    ok: !service.error, service_name: service.name ?? null,
    currentVersion: service.currentVersion ?? null,
    layer_count: Array.isArray(service.layers) ? service.layers.length : null
  };
  report.checks.layer_metadata = {
    ok: !layer.error, name: layer.name ?? null, objectIdField,
    geometryType: layer.geometryType ?? null, maxRecordCount: layer.maxRecordCount ?? null,
    fields: (layer.fields ?? []).map(f => ({ name: f.name, type: f.type, alias: f.alias }))
  };
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

  // Bounded QA sample only. Production ingestion must use a separate complete-scan routine.
  const pages = [first];
  let offset = first.features.length;
  for (let i = 1; i < MAX_PAGES && (pages.at(-1).exceededTransferLimit || pages.at(-1).features.length === PAGE_SIZE); i++) {
    const page = await queryPage(offset);
    if (!Array.isArray(page.features)) throw new Error("Paged query did not return features array");
    pages.push(page);
    offset += page.features.length;
    if (!page.features.length) break;
  }
  const all = pages.flatMap(p => p.features);
  const rawIds = all.map(f => stableId(f, objectIdField));
  const ids = rawIds.filter(v => v !== null && v !== undefined && String(v).trim() !== "").map(String);
  const uniqueIds = new Set(ids);
  const numericIds = ids.map(Number).filter(Number.isFinite);
  const idsMonotonic = numericIds.length === ids.length &&
    numericIds.every((v, i) => i === 0 || v >= numericIds[i - 1]);
  report.checks.pagination = {
    pages_checked: pages.length,
    page_sizes: pages.map(p => p.features.length),
    fetched_count: all.length,
    unique_ids: uniqueIds.size,
    duplicate_ids: ids.length - uniqueIds.size,
    missing_id_count: rawIds.length - ids.length,
    ids_monotonic_in_sample: idsMonotonic,
    capped: pages.length === MAX_PAGES && Boolean(pages.at(-1)?.exceededTransferLimit),
    complete_scan: false,
    source_total_count: countResult.count
  };

  const canonical = first.features.slice(0, 20).map(f => ({
    id: stableId(f, objectIdField), properties: f.properties, geometry_type: f.geometry?.type ?? null
  }));
  report.checks.repeatability_fingerprint = {
    sample_size: canonical.length, sha256: hash(canonical),
    note: "Compare across separate runs as a diagnostic, not proof that the source is immutable."
  };

  const businessKeys = first.features.map(f => f.properties?.Beteckn)
    .filter(v => v !== null && v !== undefined && String(v).trim() !== "").map(String);
  const uniqueBusinessKeys = new Set(businessKeys);
  const dates = first.features.map(f => f.properties?.Inkomdatum)
    .filter(v => typeof v === "number" && Number.isFinite(v));
  report.checks.field_semantics = {
    date_field_candidates: ["Inkomdatum"].filter(name => validFields.has(name)),
    status_field_candidates: ["ArendeStatus"].filter(name => validFields.has(name)),
    technical_id_field: objectIdField,
    candidate_case_key_field: validFields.has("Beteckn") ? "Beteckn" : null,
    sample_case_key_coverage: first.features.length ? businessKeys.length / first.features.length : null,
    sample_case_key_duplicates: businessKeys.length - uniqueBusinessKeys.size,
    sample_date_min: dates.length ? sourceDate(Math.min(...dates)) : null,
    sample_date_max: dates.length ? sourceDate(Math.max(...dates)) : null,
    date_field_semantics: "Inkomdatum is retained as source metadata; do not present it as first-observed or publication time.",
    identity_note: "OBJECTID is a technical row identifier. Assess its stability across independent runs; Beteckn may identify a case but must not be assumed unique without validation."
  };
  report.checks.scope = {
    requested_pages_limit: MAX_PAGES, page_size: PAGE_SIZE,
    intentionally_bounded_sample: true, count_query_used: true,
    complete_scan_attempted: false,
    note: "This probe is source QA only. It does not ingest the layer or approve alert activation."
  };

  const sampleErrors = [];
  if (all.length > countResult.count) sampleErrors.push("sample_exceeds_source_count");
  if (rawIds.length !== ids.length) sampleErrors.push("missing_id_in_sample");
  if (uniqueIds.size !== ids.length) sampleErrors.push("duplicate_id_in_sample");
  if (!idsMonotonic) sampleErrors.push("non_monotonic_or_non_numeric_ids");
  report.checks.sample_integrity = { ok: sampleErrors.length === 0, errors: sampleErrors };
  if (sampleErrors.length) throw new Error(`Sample integrity check failed: ${sampleErrors.join(", ")}`);

  report.summary = "Probe completed on a bounded sample. Alerts remain disabled; verify repeatability across at least six hours and implement a separate complete, auditable ingestion scan before any alerting.";
} catch (error) {
  report.summary = "Probe failed; alerting must remain disabled.";
  report.errors.push(String(error?.stack ?? error));
  process.exitCode = 1;
}
await mkdir("skogskoll/reports", { recursive: true });
await writeFile(OUT, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
