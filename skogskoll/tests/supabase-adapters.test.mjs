import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createArcGisSource, createSupabaseStore, createProductionAdapters } from "../src/supabase-adapters.mjs";

function response(body, { ok = true, status = 200 } = {}) {
  return {
    ok, status,
    async json() { return body; },
    async text() { return typeof body === "string" ? body : JSON.stringify(body); }
  };
}


function arcGisLayerMetadata(overrides = {}) {
  return {
    objectIdField: "OBJECTID",
    geometryType: "esriGeometryPolygon",
    hasZ: false,
    hasM: false,
    spatialReference: { wkid: 102100, latestWkid: 3857 },
    fields: [
      { name: "OBJECTID", type: "esriFieldTypeOID", nullable: false },
      { name: "Beteckn", type: "esriFieldTypeString", length: 80, nullable: true },
      { name: "Inkomdatum", type: "esriFieldTypeDate", nullable: true }
    ],
    ...overrides
  };
}

test("ArcGIS snapshot metadata is derived from the configured layer and live layer schema", async () => {
  let metadataCalls = 0;
  const fetchImpl = async url => {
    const parsed = new URL(url);
    if (parsed.pathname.endsWith("/0")) {
      metadataCalls++;
      return response(arcGisLayerMetadata());
    }
    throw new Error("Unexpected request: " + url);
  };
  const source = createArcGisSource({
    endpoint: "https://example.test/arcgis/rest/services/Harvest/MapServer/0",
    fetchImpl
  });

  const first = await source.getSnapshotMetadata();
  const second = await source.getSnapshotMetadata();
  assert.deepEqual(first, second);
  assert.equal(metadataCalls, 1, "layer metadata is cached for the source instance");
  assert.equal(first.product, "harvest_notifications");
  assert.equal(first.layer, "0");
  assert.equal(first.endpoint, "https://example.test/arcgis/rest/services/Harvest/MapServer/0");
  assert.equal(first.coverage_key, "unfiltered-layer-query-v1");
  assert.doesNotMatch(first.coverage_key, /sweden|national/i);
  assert.equal(
    first.query_definition,
    "where=1=1;outFields=*;returnGeometry=true;outSR=4326;f=geojson;orderByFields=OBJECTID ASC"
  );
  assert.match(first.schema_version, /^arcgis-layer-schema-v1:[a-f0-9]{64}$/);
  assert.equal(first.identity_version, "arcgis-oid-field:OBJECTID:geojson-id-string-v1");
  assert.equal(first.customer_visibility, "not_assessed");
  assert.equal(first.rights_evidence_ref, null);
});

test("ArcGIS schema and identity changes create new metadata versions", async () => {
  const createSource = metadata => createArcGisSource({
    endpoint: "https://example.test/arcgis/rest/services/Harvest/MapServer/0",
    fetchImpl: async () => response(metadata)
  });
  const base = await createSource(arcGisLayerMetadata()).getSnapshotMetadata();
  const changedSchema = await createSource(arcGisLayerMetadata({
    fields: [
      ...arcGisLayerMetadata().fields,
      { name: "Status", type: "esriFieldTypeString", length: 20, nullable: true }
    ]
  })).getSnapshotMetadata();
  const changedIdentity = await createSource(arcGisLayerMetadata({
    objectIdField: "ROW_ID",
    fields: [
      { name: "ROW_ID", type: "esriFieldTypeOID", nullable: false },
      ...arcGisLayerMetadata().fields.slice(1)
    ]
  })).getSnapshotMetadata();

  assert.notEqual(base.schema_version, changedSchema.schema_version);
  assert.notEqual(base.identity_version, changedIdentity.identity_version);
  assert.notEqual(base.query_definition, changedIdentity.query_definition);
});

test("ArcGIS metadata rejects an endpoint without an explicit layer number", async () => {
  const source = createArcGisSource({
    endpoint: "https://example.test/arcgis/rest/services/Harvest/MapServer",
    fetchImpl: async () => response(arcGisLayerMetadata())
  });
  await assert.rejects(source.getSnapshotMetadata(), /layer number/);
});

test("ArcGIS metadata rejects incomplete field schema", async () => {
  const source = createArcGisSource({
    endpoint: "https://example.test/arcgis/rest/services/Harvest/MapServer/0",
    fetchImpl: async () => response({ objectIdField: "OBJECTID", fields: [] })
  });
  await assert.rejects(source.getSnapshotMetadata(), /no field schema/);
});


test("ArcGIS schema fingerprint is independent of field metadata order", async () => {
  const fields = arcGisLayerMetadata().fields;
  const makeSource = orderedFields => createArcGisSource({
    endpoint: "https://example.test/arcgis/rest/services/Harvest/MapServer/0",
    fetchImpl: async () => response(arcGisLayerMetadata({ fields: orderedFields }))
  });
  const a = await makeSource(fields).getSnapshotMetadata();
  const b = await makeSource([...fields].reverse()).getSnapshotMetadata();
  assert.equal(a.schema_version, b.schema_version);
});

test("ArcGIS metadata rejects an object ID field with a non-OID type", async () => {
  const source = createArcGisSource({
    endpoint: "https://example.test/arcgis/rest/services/Harvest/MapServer/0",
    fetchImpl: async () => response(arcGisLayerMetadata({
      fields: arcGisLayerMetadata().fields.map(field =>
        field.name === "OBJECTID" ? { ...field, type: "esriFieldTypeInteger" } : field
      )
    }))
  });
  await assert.rejects(source.getSnapshotMetadata(), /not typed as an OID/);
  await assert.rejects(source.getSnapshotMetadata(), /not typed as an OID/);
});

test("ArcGIS source returns count and normalizes object IDs", async () => {
  const calls = [];
  const fetchImpl = async url => {
    calls.push(String(url));
    const parsed = new URL(url);
    if (parsed.pathname.endsWith("/0")) {
      return response({ objectIdField: "OBJECTID", fields: [{ name: "OBJECTID", type: "esriFieldTypeOID" }] });
    }
    if (parsed.searchParams.get("returnCountOnly") === "true") return response({ count: 2 });
    return response({ type: "FeatureCollection", features: [
      { type: "Feature", properties: { OBJECTID: 10 }, geometry: null },
      { type: "Feature", properties: { OBJECTID: 11 }, geometry: null }
    ] });
  };
  const source = createArcGisSource({ endpoint: "https://example.test/MapServer/0", fetchImpl });
  assert.equal(await source.getCount(), 2);
  const page = await source.getPage(0, 2);
  assert.deepEqual(page.features.map(f => f.id), ["10", "11"]);
  assert.equal(page.exceededTransferLimit, false);
  assert.ok(calls.some(url => url.includes("orderByFields=OBJECTID")));
});

test("Supabase store restores compact checkpoint without downloading all seen IDs", async () => {
  const calls = [];
  const fetchImpl = async url => {
    calls.push(String(url));
    const parsed = new URL(url);
    if (parsed.pathname.endsWith("/scan_sessions")) return response([{
      id: "scan-1", source: "source-a", source_count: 3, page_size: 2,
      next_offset: 2, fetched_count: 2, status: "running",
      diagnostics: { mode: "incremental", snapshot_metadata: { product: "harvest_notifications", schema_version: "schema-v1" } }, updated_at: "2026-10-25T00:00:00Z"
    }]);
    throw new Error("Unexpected request: " + url);
  };
  const store = createSupabaseStore({
    url: "https://project.supabase.co", serviceRoleKey: "test-key",
    fetchImpl, restBatchSize: 2
  });
  const checkpoint = await store.loadCheckpoint("source-a");
  assert.equal(checkpoint.scanId, "scan-1");
  assert.equal(checkpoint.mode, "incremental");
  assert.deepEqual(checkpoint.snapshotMetadata, { product: "harvest_notifications", schema_version: "schema-v1" });
  assert.deepEqual(checkpoint.seenIds, []);
  assert.equal(checkpoint.externalSeenIds, true);
  assert.equal(checkpoint.seenIdsCount, 2);
  assert.equal(checkpoint.complete, false);
  assert.equal(calls.length, 1, "resume requires only one checkpoint query");
  assert.equal(store.externalSeenIds, true);
});

test("Supabase start scan calls RPC with explicit mode", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), init });
    return response([{ scan_id: "scan-42", poll_run_id: "run-42" }]);
  };
  const store = createSupabaseStore({
    url: "https://project.supabase.co", serviceRoleKey: "test-key", fetchImpl
  });
  const id = await store.startScan({ sourceKey: "src", reportedTotal: 12, pageSize: 500, mode: "incremental" });
  assert.equal(id, "scan-42");
  assert.ok(calls[0].url.endsWith("/rest/v1/rpc/skogskoll_start_scan"));
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    p_source: "src", p_source_count: 12, p_page_size: 500, p_mode: "incremental", p_snapshot_metadata: null
  });
});

test("adapter refuses missing Supabase credentials before making requests", () => {
  assert.throws(() => createProductionAdapters({}, {}), /SUPABASE_URL/);
  assert.throws(() => createSupabaseStore({ url: "https://project.supabase.co", serviceRoleKey: "" }), /service-role key/);
});

test("manual ingestion entrypoint is disabled without explicit opt-in", () => {
  const script = new URL("../scripts/run-scan.mjs", import.meta.url);
  const env = { ...process.env };
  delete env.SKOGSKOLL_ENABLE_INGESTION;
  delete env.SKOGSKOLL_SCAN_MODE;
  delete env.SUPABASE_URL;
  delete env.SUPABASE_SERVICE_ROLE_KEY;
  const result = spawnSync(process.execPath, [fileURLToPath(script)], {
    encoding: "utf8",
    env
  });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Ingestion is disabled/);
  assert.doesNotMatch(result.stderr, /SUPABASE_SERVICE_ROLE_KEY/);
});

test("stale scan recovery RPC is narrowly scoped and requires explicit age cutoff", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), init });
    return response([{ recovered_scan_id: "scan-old", recovered_offset: 1500 }]);
  };
  const store = createSupabaseStore({
    url: "https://project.supabase.co", serviceRoleKey: "test-key", fetchImpl
  });
  const result = await store.recoverStaleScan({
    sourceKey: "source-a",
    staleBefore: "2026-10-25T08:00:00Z",
    reason: "worker interrupted"
  });
  assert.deepEqual(result, [{ recovered_scan_id: "scan-old", recovered_offset: 1500 }]);
  assert.ok(calls[0].url.endsWith("/rest/v1/rpc/skogskoll_recover_stale_scan"));
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    p_source: "source-a",
    p_stale_before: "2026-10-25T08:00:00Z",
    p_reason: "worker interrupted"
  });
});

test("manual stale recovery command is disabled without explicit opt-in", () => {
  const script = new URL("../scripts/recover-stale-scan.mjs", import.meta.url);
  const env = { ...process.env };
  delete env.SKOGSKOLL_ENABLE_STALE_RECOVERY;
  delete env.SUPABASE_URL;
  delete env.SUPABASE_SERVICE_ROLE_KEY;
  const result = spawnSync(process.execPath, [fileURLToPath(script)], {
    encoding: "utf8",
    env
  });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Stale-session recovery is disabled/);
  assert.doesNotMatch(result.stderr, /SUPABASE_SERVICE_ROLE_KEY/);
});

test("Supabase start scan binds immutable source metadata to the run", async () => {
  const calls = [];
  const metadata = {
    product: "harvest_notifications",
    endpoint: "https://example.test/MapServer/0",
    layer: "0",
    query_definition: "where=1=1",
    coverage_key: "unfiltered-layer-query-v1",
    schema_version: "schema-v1",
    identity_version: "oid-v1",
    customer_visibility: "not_assessed",
    rights_evidence_ref: null
  };
  const store = createSupabaseStore({
    url: "https://project.supabase.co", serviceRoleKey: "test-key",
    fetchImpl: async (url, init) => {
      calls.push({ url: String(url), init });
      return response([{ scan_id: "scan-42", poll_run_id: "run-42" }]);
    }
  });
  await store.startScan({ sourceKey: "src", reportedTotal: 2, pageSize: 2, mode: "baseline", snapshotMetadata: metadata });
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    p_source: "src", p_source_count: 2, p_page_size: 2, p_mode: "baseline", p_snapshot_metadata: metadata
  });
});

test("Supabase finish registers a validated immutable snapshot envelope", async () => {
  const calls = [];
  const metadata = {
    product: "harvest_notifications",
    endpoint: "https://example.test/MapServer/0",
    layer: "0",
    query_definition: "where=1=1",
    coverage_key: "unfiltered-layer-query-v1",
    schema_version: "schema-v1",
    identity_version: "oid-v1",
    customer_visibility: "not_assessed",
    rights_evidence_ref: null
  };
  const fetchImpl = async (url, init = {}) => {
    const parsed = new URL(url);
    calls.push({ url: String(url), method: init.method ?? "GET", body: init.body ? JSON.parse(init.body) : null });
    if (parsed.pathname.endsWith("/rpc/skogskoll_finish_scan")) return response(null);
    if (parsed.pathname.endsWith("/scan_sessions")) return response([{
      id: "scan-42", source: "src", source_count: 2, fetched_count: 2, next_offset: 2,
      status: "complete", completed_at: "2026-11-23T07:00:00.000Z", poll_run_id: "run-42",
      diagnostics: { snapshot_metadata: metadata }
    }]);
    if (parsed.pathname.endsWith("/poll_runs")) return response([{
      id: "run-42", source: "src", status: "success", fetched_count: 2,
      finished_at: "2026-11-23T07:00:00.000Z", diagnostics: {}
    }]);
    if (parsed.pathname.endsWith("/rpc/skogskoll_register_snapshot")) return response("skogskoll-worker:run-42:scan-42");
    throw new Error("Unexpected request: " + url);
  };
  const store = createSupabaseStore({ url: "https://project.supabase.co", serviceRoleKey: "test-key", fetchImpl });
  await store.finishScan("scan-42");
  const registration = calls.find(call => call.url.endsWith("/rpc/skogskoll_register_snapshot"));
  assert.ok(registration);
  assert.equal(registration.body.p_scan_id, "scan-42");
  assert.equal(registration.body.p_envelope.status, "complete");
  assert.equal(registration.body.p_envelope.customer_visibility, "not_assessed");
  assert.equal(registration.body.p_envelope.snapshot_id, "skogskoll-worker:run-42:scan-42");
});

test("Supabase store enumerates and registers terminal scans missing envelopes", async () => {
  const calls = [];
  const metadata = {
    product: "harvest_notifications",
    endpoint: "https://example.test/MapServer/0",
    layer: "0",
    query_definition: "where=1=1",
    coverage_key: "unfiltered-layer-query-v1",
    schema_version: "schema-v1",
    identity_version: "oid-v1",
    customer_visibility: "not_assessed",
    rights_evidence_ref: null
  };
  const fetchImpl = async (url, init = {}) => {
    const parsed = new URL(url);
    calls.push({ url: String(url), init });
    if (parsed.pathname.endsWith("/rpc/skogskoll_pending_snapshot_scans")) return response([{ scan_id: "scan-pending" }]);
    if (parsed.pathname.endsWith("/scan_sessions")) return response([{
      id: "scan-pending", source: "source-a", source_count: 1, fetched_count: 1, next_offset: 1,
      status: "complete", completed_at: "2026-11-23T07:00:00.000Z", poll_run_id: "run-pending",
      diagnostics: { snapshot_metadata: metadata }
    }]);
    if (parsed.pathname.endsWith("/poll_runs")) return response([{
      id: "run-pending", source: "source-a", status: "success", fetched_count: 1,
      finished_at: "2026-11-23T07:00:00.000Z", diagnostics: {}
    }]);
    if (parsed.pathname.endsWith("/rpc/skogskoll_register_snapshot")) return response("snapshot-registered");
    throw new Error("Unexpected request: " + url);
  };
  const store = createSupabaseStore({ url: "https://project.supabase.co", serviceRoleKey: "test-key", fetchImpl });
  const count = await store.registerPendingSnapshots("source-a");
  assert.equal(count, 1);
  assert.ok(calls[0].url.endsWith("/rpc/skogskoll_pending_snapshot_scans"));
  assert.deepEqual(JSON.parse(calls[0].init.body), { p_source: "source-a" });
  assert.ok(calls[1].url.includes("/scan_sessions?"));
  assert.ok(calls[2].url.includes("/poll_runs?"));
  assert.ok(calls[3].url.endsWith("/rpc/skogskoll_register_snapshot"));
});
