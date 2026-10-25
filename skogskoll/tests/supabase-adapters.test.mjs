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
      diagnostics: { mode: "incremental" }, updated_at: "2026-10-25T00:00:00Z"
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
    p_source: "src", p_source_count: 12, p_page_size: 500, p_mode: "incremental"
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
