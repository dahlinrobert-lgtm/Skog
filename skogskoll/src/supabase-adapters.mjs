import { SOURCE_ID } from "../src/observation-core.mjs";

const DEFAULT_ENDPOINT = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer/0";
const DEFAULT_PAGE_LIMIT = 1000;
const REST_BATCH_SIZE = 1000;

function requiredEnv(env, name) {
  const value = env[name];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value.trim();
}

function arcGisId(feature, objectIdField) {
  const properties = feature?.properties ?? {};
  const value = feature?.id ?? properties[objectIdField] ?? properties.OBJECTID ?? properties.ObjectId ?? properties.objectid;
  return value === null || value === undefined || String(value).trim() === "" ? null : String(value);
}

async function fetchJson(url, init = {}) {
  const response = await fetch(url, {
    ...init,
    headers: {
      "user-agent": "Skogskoll-ingestion-worker/0.1 (server-side; bounded scan)",
      ...(init.headers ?? {})
    }
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(`HTTP ${response.status} from ${new URL(url).origin}`);
  if (!body || typeof body !== "object") throw new Error("Upstream returned invalid JSON");
  if (body.error) throw new Error(body.error.message || JSON.stringify(body.error));
  return body;
}

export function createArcGisSource({
  endpoint = DEFAULT_ENDPOINT,
  pageLimit = DEFAULT_PAGE_LIMIT,
  fetchImpl = fetch
} = {}) {
  if (!Number.isSafeInteger(pageLimit) || pageLimit < 1) throw new TypeError("pageLimit must be a positive integer");
  const queryEndpoint = endpoint.replace(/\/$/, "") + "/query";
  let objectIdField = null;

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

  async function getObjectIdField() {
    if (objectIdField) return objectIdField;
    const metadata = await json(endpoint.replace(/\/$/, "") + "?f=pjson");
    objectIdField = metadata.objectIdField ?? metadata.objectIdFieldName ??
      (metadata.fields ?? []).find(field => field.type === "esriFieldTypeOID")?.name;
    if (!objectIdField) throw new Error("ArcGIS layer metadata has no object ID field");
    return objectIdField;
  }

  return {
    key: SOURCE_ID,
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
      const url = queryEndpoint + "?" + new URLSearchParams({
        where: "1=1",
        outFields: "*",
        returnGeometry: "true",
        outSR: "4326",
        f: "geojson",
        resultRecordCount: String(size),
        orderByFields: `${idField} ASC`,
        resultOffset: String(offset)
      });
      const body = await json(url);
      if (!Array.isArray(body.features)) throw new Error("ArcGIS page omitted features array");
      return { features: body.features, exceededTransferLimit: body.exceededTransferLimit === true };
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

  async function listSeenIds(scanId) {
    const ids = [];
    for (let offset = 0; ; offset += restBatchSize) {
      const query = new URLSearchParams({
        select: "source_id,first_offset",
        scan_id: `eq.${scanId}`,
        order: "first_offset.asc",
        limit: String(restBatchSize),
        offset: String(offset)
      });
      const batch = await request(`/rest/v1/scan_seen_ids?${query}`);
      if (!Array.isArray(batch)) throw new Error("Unexpected scan_seen_ids response");
      ids.push(...batch.map(row => String(row.source_id)));
      if (batch.length < restBatchSize) break;
    }
    return ids;
  }

  return {
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
      const seenIds = await listSeenIds(row.id);
      const checkpoint = {
        schemaVersion: 1,
        sourceKey: row.source,
        reportedTotal: row.source_count,
        pageSize: row.page_size,
        nextOffset: row.next_offset,
        fetchedCount: row.fetched_count,
        seenIds,
        updatedAt: row.updated_at ?? null,
        complete: row.next_offset === row.source_count && row.fetched_count === row.source_count,
        scanId: row.id,
        mode: row.diagnostics?.mode ?? "baseline"
      };
      if (seenIds.length !== checkpoint.fetchedCount) {
        // Do not silently reset or advance a broken persisted checkpoint.
        throw new Error(`Persisted checkpoint has ${seenIds.length} IDs but fetched_count is ${checkpoint.fetchedCount}`);
      }
      return checkpoint;
    },

    async startScan({ sourceKey, reportedTotal, pageSize, mode = "baseline" }) {
      const result = await rpc("skogskoll_start_scan", {
        p_source: sourceKey,
        p_source_count: reportedTotal,
        p_page_size: pageSize,
        p_mode: mode
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

    async finishScan(scanId) {
      await rpc("skogskoll_finish_scan", { p_scan_id: scanId });
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
