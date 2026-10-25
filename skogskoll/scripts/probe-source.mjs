import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";

const SERVICE = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer";
const ENDPOINT = SERVICE + "/0";
const OUT = "skogskoll/reports/source-probe-latest.json";
const PAGE_SIZE = 100;
const MAX_PAGES = 3;
const fields = ["OBJECTID", "Beteckn", "Kommun", "Inkomdatum", "ArendeStatus", "AnmaldHa"];

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
function stableId(feature) {
  return feature.id ?? feature.properties?.OBJECTID ?? feature.properties?.ObjectId ?? null;
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
  const [service, layer, first] = await Promise.all([
    getJson(ENDPOINT + "?f=pjson"),
    getJson(ENDPOINT + "?f=pjson"),
    getJson(ENDPOINT + "/query?" + new URLSearchParams({
      where: "1=1", outFields: fields.join(","), returnGeometry: "true",
      outSR: "4326", f: "geojson", resultRecordCount: String(PAGE_SIZE),
      orderByFields: "OBJECTID ASC", resultOffset: "0"
    }))
  ]);
  report.checks.service_metadata = {
    ok: !service.error, service_name: service.name ?? null,
    currentVersion: service.currentVersion ?? null,
    layer_count: Array.isArray(service.layers) ? service.layers.length : null
  };
  report.checks.layer_metadata = {
    ok: !layer.error, name: layer.name ?? null, objectIdField: layer.objectIdField ?? null,
    geometryType: layer.geometryType ?? null, maxRecordCount: layer.maxRecordCount ?? null,
    fields: (layer.fields ?? []).map(f => ({ name: f.name, type: f.type, alias: f.alias }))
  };
  if (!Array.isArray(first.features)) throw new Error("Query did not return a GeoJSON features array");
  report.checks.first_page = {
    ok: true, count: first.features.length,
    response_type: first.type ?? null,
    has_exceededTransferLimit: Boolean(first.exceededTransferLimit),
    sample_ids: first.features.slice(0, 10).map(stableId),
    sample_properties: first.features.slice(0, 3).map(f => f.properties),
    geometry_types: [...new Set(first.features.map(f => f.geometry?.type ?? "null"))],
    stable_id_coverage: first.features.length
      ? first.features.filter(f => stableId(f) !== null).length / first.features.length : null
  };
  const pages = [first];
  let offset = first.features.length;
  for (let i = 1; i < MAX_PAGES && (first.exceededTransferLimit || first.features.length === PAGE_SIZE); i++) {
    const page = await getJson(ENDPOINT + "/query?" + new URLSearchParams({
      where: "1=1", outFields: fields.join(","), returnGeometry: "true",
      outSR: "4326", f: "geojson", resultRecordCount: String(PAGE_SIZE),
      orderByFields: "OBJECTID ASC", resultOffset: String(offset)
    }));
    if (!Array.isArray(page.features)) throw new Error("Paged query did not return features array");
    pages.push(page);
    offset += page.features.length;
    if (!page.features.length) break;
  }
  const all = pages.flatMap(p => p.features);
  const ids = all.map(stableId).filter(v => v !== null).map(String);
  report.checks.pagination = {
    pages_checked: pages.length, fetched_count: all.length,
    unique_ids: new Set(ids).size, duplicate_ids: ids.length - new Set(ids).size,
    ids_monotonic_in_sample: ids.every((v, i) => i === 0 || Number(v) >= Number(ids[i - 1])),
    capped: pages.length === MAX_PAGES && Boolean(pages.at(-1)?.exceededTransferLimit)
  };
  const canonical = first.features.slice(0, 20).map(f => ({
    id: stableId(f), properties: f.properties, geometry_type: f.geometry?.type ?? null
  }));
  report.checks.repeatability_fingerprint = {
    sample_size: canonical.length,
    sha256: hash(canonical),
    note: "Compare this fingerprint across separate runs; it is a diagnostic, not proof of source immutability."
  };
  report.checks.field_semantics = {
    date_field_candidates: ["Inkomdatum"].filter(name =>
      (layer.fields ?? []).some(f => f.name === name)),
    status_field_candidates: ["ArendeStatus"].filter(name =>
      (layer.fields ?? []).some(f => f.name === name)),
    id_field_detected: layer.objectIdField ?? null,
    note: "Confirm actual field types and whether Inkomdatum means received date or another date before user-facing wording."
  };
  report.summary = "Probe completed. This is not approval to activate alerts; repeat at least twice across a six-hour interval and review field semantics, stable IDs, pagination and geometry.";
} catch (error) {
  report.summary = "Probe failed; alerting must remain disabled.";
  report.errors.push(String(error?.stack ?? error));
  process.exitCode = 1;
}
await mkdir("skogskoll/reports", { recursive: true });
await writeFile(OUT, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
