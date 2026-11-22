import { createHash } from "node:crypto";
import { SOURCE_ID } from "../src/observation-core.mjs";
import { mapWorkerScanToSnapshotEnvelope } from "./snapshot-envelope-adapter.mjs";

const DEFAULT_ENDPOINT = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer/0";
const DEFAULT_PAGE_LIMIT = 1000;
const REST_BATCH_SIZE = 1000;
const DEFAULT_PRODUCT = "harvest_notifications";
const COVERAGE_KEY = "unfiltered-layer-query-v1";

function requiredEnv(env, name) {
  const value = env[name];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value.trim();
}

export function createArcGisSource({
  endpoint = DEFAULT_ENDPOINT,
  product = DEFAULT_PRODUCT,
  pageLimit = DEFAULT_PAGE_LIMIT,
  fetchImpl = fetch
} = {}) {
  if (!Number.isSafeInteger(pageLimit) || pageLimit < 1) throw new TypeError("pageLimit must be a positive integer");
  if (typeof product !== "string" || product.trim() === "") throw new TypeError("product must be a non-empty string");
  const normalizedEndpoint = endpoint.replace(/\/$/, "");
  const queryEndpoint = normalizedEndpoint + "/query";
  let objectIdField = null;
  let layerMetadata = null;

  async function json(url) {
    const response = await fetchImpl(url, {
      headers: { "user-agent": "Skogskoll-ingestion-worker/0.1 (server-side; bounded scan)" }
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(`ArcGIS HTTP ${response.status}`);
    if (!body || typeof body !== "object") throw new Error("ArcGIS returned invalid JSON");
    if (body.error) throw new Error(body.error.message || JSON.stringify(body.error));
    return body;
  }

  async function getLayerMetadata() {
    if (layerMetadata) return layerMetadata;
    const metadata = await json(normalizedEndpoint + "?f=pjson");
    if (!Array.isArray(metadata.fields) || metadata.fields.length === 0) {
      throw new Error("ArcGIS layer metadata has no field schema");
    }
    layerMetadata = metadata;
    return layerMetadata;
  }

  async function getObjectIdField() {
    if (objectIdField) return objectIdField;
    const metadata = await getLayerMetadata();
    const candidate = metadata.objectIdField ?? metadata.objectIdFieldName ??
      metadata.fields.find(field => field.type === "esriFieldTypeOID")?.name;
    if (typeof candidate !== "string" || candidate.trim() === "") {
      throw new Error("ArcGIS layer metadata has no object ID field");
    }
    const idFieldMetadata = metadata.fields.find(field => field.name === candidate);
    if (!idFieldMetadata) throw new Error("ArcGIS object ID field is not present in layer fields");
    if (idFieldMetadata.type !== "esriFieldTypeOID") {
      throw new Error("ArcGIS object ID field is not typed as an OID");
    }
    objectIdField = candidate;
    return objectIdField;
  }

  function featureQueryParameters(idField) {
    return {
      where: "1=1",
      outFields: "*",
      returnGeometry: "true",
      outSR: "4326",
      f: "geojson",
      orderByFields: `${idField} ASC`
    };
  }

  function canonicalize(value) {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value && typeof value === "object") {
      return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonicalize(value[key])]));
    }
    return value;
  }

  async function getSnapshotMetadata() {
    const metadata = await getLayerMetadata();
    const idField = await getObjectIdField();
    const layerMatch = normalizedEndpoint.match(/\/(?:MapServer|FeatureServer)\/(\d+)$/i);
    if (!layerMatch) throw new Error("ArcGIS endpoint does not identify a MapServer/FeatureServer layer number");
    if (typeof metadata.geometryType !== "string" || metadata.geometryType === "") {
      throw new Error("ArcGIS layer metadata has no geometry type");
    }

    const fields = metadata.fields.map(field => {
      if (typeof field.name !== "string" || field.name === "" ||
          typeof field.type !== "string" || field.type === "") {
        throw new Error("ArcGIS layer metadata contains an invalid field definition");
      }
      return {
        name: field.name,
        type: field.type,
        length: Number.isSafeInteger(field.length) ? field.length : null,
        nullable: typeof field.nullable === "boolean" ? field.nullable : null,
        domain: canonicalize(field.domain ?? null)
      };
    }).sort((a, b) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0);

    if (new Set(fields.map(field => field.name)).size !== fields.length) {
      throw new Error("ArcGIS layer metadata contains duplicate field names");
    }

    const schemaDescriptor = canonicalize({
      fields,
      geometry_type: metadata.geometryType,
      has_z: metadata.hasZ === true,
      has_m: metadata.hasM === true,
      source_spatial_reference: metadata.spatialReference?.latestWkid ??
        metadata.spatialReference?.wkid ?? null,
      output_spatial_reference: "EPSG:4326"
    });
    const schemaDigest = createHash("sha256")
      .update(JSON.stringify(schemaDescriptor))
      .digest("hex");

    return {
      product,
      endpoint: normalizedEndpoint,
      layer: layerMatch[1],
      // Pagination controls are deliberately excluded: changing page size or
      // offset does not change the logical set of source features.
      query_definition: Object.entries(featureQueryParameters(idField))
        .map(([key, value]) => `${key}=${value}`)
        .join(";"),
      // This identifies the unfiltered layer query, not a claim of national
      // geographic coverage or a verified source completeness statement.
      coverage_key: COVERAGE_KEY,
      schema_version: `arcgis-layer-schema-v1:${schemaDigest}`,
      // The field is the ArcGIS technical OID mapped to a string GeoJSON id.
      // This does not assert that the provider preserves OIDs indefinitely.
      identity_version: `arcgis-oid-field:${idField}:geojson-id-string-v1`,
      customer_visibility: "not_assessed",
      rights_evidence_ref: null
    };
  }

  return {
    key: SOURCE_ID,
    getSnapshotMetadata,
    async getCount() {
      const body = await json(queryEndpoint + "?" + new URLSearchParams({
        where: "1=1", returnCountOnly: "true", f: "json"
      }));
      if (!Number.isSafeInteger(body.count) || body.count < 0) throw new Error("ArcGIS returned invalid count");
      return body.count;
    },
    async getPage(offset, requestedSize) {
      const idField = await getObjectIdField();
      const size = Math.min(requestedSize, pageLimit);
      const query = featureQueryParameters(idField);
      const url = queryEndpoint + "?" + new URLSearchParams({
        ...query,
        resultRecordCount: String(size),
        resultOffset: String(offset)
      });
      const body = await json(url);
      if (!Array.isArray(body.features)) throw new Error("ArcGIS page omitted features array");
      // Normalize the technical key regardless of GeoJSON's id representation.
      const features = body.features.map(feature => {
        const properties = feature.properties ?? {};
        const id = feature.id ?? properties[idField] ?? properties.OBJECTID ?? properties.ObjectId ?? properties.objectid;
        return id === null || id === undefined ? feature : { ...feature, id: String(id) };
      });
      return { features, exceededTransferLimit: body.exceededTransferLimit === true };
    }
  };
}

export function createSupabaseStore({
  url,
  serviceRoleKey,
  fetchImpl = fetch,
  restBatchSize = REST_BATCH_SIZE
}) {
  if (typeof url !== "string" || !/^https:\/\//.test(url)) throw new TypeError("A valid HTTPS Supabase URL is required");
  if (typeof serviceRoleKey !== "string" || serviceRoleKey.trim() === "") throw new TypeError("Supabase service-role key is required");
  if (!Number.isSafeInteger(restBatchSize) || restBatchSize < 1) throw new TypeError("restBatchSize must be positive");
  const base = url.replace(/\/$/, "");
  const headers = {
    apikey: serviceRoleKey,
    authorization: `Bearer ${serviceRoleKey}`,
    "content-type": "application/json"
  };

  async function request(path, { method = "GET", body, headers: extraHeaders = {} } = {}) {
    const response = await fetchImpl(base + path, {
      method,
      headers: { ...headers, ...extraHeaders },
      ...(body === undefined ? {} : { body: JSON.stringify(body) })
    });
    const text = await response.text();
    const payload = text ? (() => { try { return JSON.parse(text); } catch { return text; } })() : null;
    if (!response.ok) {
      const detail = typeof payload === "string" ? payload : JSON.stringify(payload);
      throw new Error(`Supabase REST ${response.status}: ${detail.slice(0, 900)}`);
    }
    return payload;
  }

  async function rpc(name, args) {
    return request(`/rest/v1/rpc/${name}`, { method: "POST", body: args });
  }

  return {
    externalSeenIds: true,
    async loadCheckpoint(sourceKey) {
      const query = new URLSearchParams({
        select: "id,source,source_count,page_size,next_offset,fetched_count,status,diagnostics,updated_at",
        source: `eq.${sourceKey}`,
        status: "eq.running",
        order: "updated_at.desc",
        limit: "1"
      });
      const rows = await request(`/rest/v1/scan_sessions?${query}`);
      if (!Array.isArray(rows)) throw new Error("Unexpected scan_sessions response");
      if (!rows.length) return null;
      const row = rows[0];
      const checkpoint = {
        schemaVersion: 1,
        sourceKey: row.source,
        reportedTotal: row.source_count,
        pageSize: row.page_size,
        nextOffset: row.next_offset,
        fetchedCount: row.fetched_count,
        seenIds: [],
        externalSeenIds: true,
        seenIdsCount: row.fetched_count,
        updatedAt: row.updated_at ?? null,
        complete: row.next_offset === row.source_count && row.fetched_count === row.source_count,
        scanId: row.id,
        mode: row.diagnostics?.mode ?? "baseline",
        snapshotMetadata: row.diagnostics?.snapshot_metadata ?? null
      };
      if (checkpoint.reportedTotal < 0 || checkpoint.nextOffset > checkpoint.reportedTotal ||
          checkpoint.fetchedCount !== checkpoint.nextOffset) {
        await rpc("skogskoll_fail_scan", {
          p_scan_id: row.id,
          p_reason: "persisted_checkpoint_inconsistent",
          p_details: {
            source_count: checkpoint.reportedTotal,
            next_offset: checkpoint.nextOffset,
            fetched_count: checkpoint.fetchedCount
          }
        });
        throw new Error("Persisted scan checkpoint exceeds or conflicts with its recorded source count");
      }
      return checkpoint;
    },

    async startScan({ sourceKey, reportedTotal, pageSize, mode = "baseline", snapshotMetadata = null }) {
      const result = await rpc("skogskoll_start_scan", {
        p_source: sourceKey,
        p_source_count: reportedTotal,
        p_page_size: pageSize,
        p_mode: mode,
        p_snapshot_metadata: snapshotMetadata
      });
      const row = Array.isArray(result) ? result[0] : result;
      if (!row?.scan_id) throw new Error("Supabase start-scan RPC returned no scan_id");
      return row.scan_id;
    },

    async commitPage({ scanId, previousCheckpoint, nextCheckpoint, records, pageIds }) {
      if (!Array.isArray(records) || !Array.isArray(pageIds)) throw new TypeError("commitPage needs records and pageIds arrays");
      const observedAt = nextCheckpoint.updatedAt;
      const result = await rpc("skogskoll_commit_page", {
        p_scan_id: scanId,
        p_expected_offset: previousCheckpoint.nextOffset,
        p_expected_fetched: previousCheckpoint.fetchedCount,
        p_next_offset: nextCheckpoint.nextOffset,
        p_next_fetched: nextCheckpoint.fetchedCount,
        p_records: records.map(({ ok, ...record }) => record),
        p_ids: pageIds,
        p_observed_at: observedAt
      });
      return result;
    },

    async finishScan(scanId, checkpoint, snapshotMetadata = null) {
      await rpc("skogskoll_finish_scan", { p_scan_id: scanId });
      if (!snapshotMetadata) return;
      const scanQuery = new URLSearchParams({
        select: "id,source,source_count,fetched_count,next_offset,status,completed_at,diagnostics",
        id: `eq.${scanId}`,
        limit: "1"
      });
      const scanRows = await request(`/rest/v1/scan_sessions?${scanQuery}`);
      if (!Array.isArray(scanRows) || scanRows.length !== 1) {
        throw new Error("Completed scan session could not be reloaded for snapshot registration");
      }
      const scan = scanRows[0];
      const runId = scanRows[0].diagnostics?.poll_run_id ?? null;
      const pollRunId = runId ?? checkpoint?.pollRunId ?? null;
      if (!pollRunId) {
        const runQuery = new URLSearchParams({
          select: "id,source,status,fetched_count,finished_at,diagnostics",
          id: `eq.${scanId}`,
          limit: "1"
        });
        void runQuery;
      }
      const linkedRunId = scan.poll_run_id ?? pollRunId;
      if (!linkedRunId) throw new Error("Completed scan has no poll_run_id for snapshot registration");
      const runQuery = new URLSearchParams({
        select: "id,source,status,fetched_count,finished_at,diagnostics",
        id: `eq.${linkedRunId}`,
        limit: "1"
      });
      const runRows = await request(`/rest/v1/poll_runs?${runQuery}`);
      if (!Array.isArray(runRows) || runRows.length !== 1) {
        throw new Error("Poll run could not be reloaded for snapshot registration");
      }
      const mapped = mapWorkerScanToSnapshotEnvelope({
        pollRun: runRows[0],
        scanSession: scan,
        metadata: scan.diagnostics?.snapshot_metadata ?? snapshotMetadata
      });
      if (!mapped.valid || mapped.envelope.status !== "complete") {
        throw new Error("Snapshot envelope validation failed: " + mapped.errors.join(", "));
      }
      await rpc("skogskoll_register_snapshot", {
        p_scan_id: scanId,
        p_envelope: mapped.envelope
      });
    },

    async recoverStaleScan({ sourceKey, staleBefore, reason = "stale_worker_recovery" }) {
      if (typeof sourceKey !== "string" || sourceKey.trim() === "") throw new TypeError("sourceKey is required");
      if (typeof staleBefore !== "string" || !Number.isFinite(Date.parse(staleBefore)) || Date.parse(staleBefore) >= Date.now()) {
        throw new TypeError("staleBefore must be a valid timestamp in the past");
      }
      return rpc("skogskoll_recover_stale_scan", {
        p_source: sourceKey,
        p_stale_before: staleBefore,
        p_reason: String(reason).slice(0, 500)
      });
    },

    async failScan(scanId, reason, details = {}) {
      if (!scanId) return;
      await rpc("skogskoll_fail_scan", {
        p_scan_id: scanId,
        p_reason: String(reason ?? "unknown").slice(0, 500),
        p_details: details
      });
    }
  };
}

export function createProductionAdapters(env = process.env, options = {}) {
  return {
    source: createArcGisSource(options.source),
    store: createSupabaseStore({
      url: requiredEnv(env, "SUPABASE_URL"),
      serviceRoleKey: requiredEnv(env, "SUPABASE_SERVICE_ROLE_KEY"),
      ...(options.store ?? {})
    })
  };
}
