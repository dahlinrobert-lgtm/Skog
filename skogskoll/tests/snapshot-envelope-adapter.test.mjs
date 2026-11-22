import test from "node:test";
import assert from "node:assert/strict";
import {
  buildComparabilityKey,
  mapWorkerScanToSnapshotEnvelope
} from "../src/snapshot-envelope-adapter.mjs";

const pollRun = {
  id: "run-001",
  source: "skogsstyrelsen:avverkningsanmalan",
  status: "success",
  fetched_count: 2,
  finished_at: "2026-11-23T07:00:00.000Z"
};
const scanSession = {
  id: "scan-001",
  source: "skogsstyrelsen:avverkningsanmalan",
  status: "complete",
  source_count: 2,
  fetched_count: 2,
  next_offset: 2,
  completed_at: "2026-11-23T07:00:00.000Z"
};
const metadata = {
  product: "harvest_notifications",
  endpoint: "https://example.test/arcgis/MapServer/0",
  layer: "0",
  query_definition: "where=1=1;outFields=*;returnGeometry=true;outSR=4326;f=geojson;orderByFields=OBJECTID ASC",
  coverage_key: "grasmyr-10km-v1",
  schema_version: "1",
  identity_version: "arcgis-objectid-v1"
};

test("complete reconciled scan maps to complete without customer approval", () => {
  const r = mapWorkerScanToSnapshotEnvelope({ pollRun, scanSession, metadata });
  assert.equal(r.valid, true);
  assert.equal(r.envelope.status, "complete");
  assert.equal(r.envelope.customer_visibility, "not_assessed");
  assert.equal(r.envelope.rights_evidence_ref, null);
  assert.ok(r.envelope.comparability_key);
});

test("partial scan never maps to complete", () => {
  const r = mapWorkerScanToSnapshotEnvelope({
    pollRun: { ...pollRun, status: "warning" },
    scanSession: { ...scanSession, status: "running", fetched_count: 1, next_offset: 1 },
    metadata
  });
  assert.equal(r.envelope.status, "partial");
  assert.ok(r.envelope.diagnostics.completeness_reasons.length);
});

test("failed scan maps to failed", () => {
  const r = mapWorkerScanToSnapshotEnvelope({
    pollRun: { ...pollRun, status: "failed" },
    scanSession: { ...scanSession, status: "failed" },
    metadata
  });
  assert.equal(r.envelope.status, "failed");
});

test("count mismatch prevents complete status", () => {
  const r = mapWorkerScanToSnapshotEnvelope({
    pollRun,
    scanSession: { ...scanSession, fetched_count: 1, next_offset: 1 },
    metadata
  });
  assert.equal(r.envelope.status, "partial");
  assert.ok(r.envelope.diagnostics.completeness_reasons.includes("scan_count_mismatch"));
});

test("missing coverage metadata is rejected, never guessed", () => {
  const r = mapWorkerScanToSnapshotEnvelope({
    pollRun,
    scanSession,
    metadata: { ...metadata, coverage_key: "" }
  });
  assert.equal(r.valid, false);
  assert.ok(r.errors.includes("metadata_missing_coverage_key"));
});

test("source mismatch is rejected", () => {
  const r = mapWorkerScanToSnapshotEnvelope({
    pollRun,
    scanSession: { ...scanSession, source: "other" },
    metadata
  });
  assert.equal(r.valid, false);
  assert.ok(r.errors.includes("source_mismatch"));
});

test("endpoint changes create a new comparison basis", () => {
  const a = buildComparabilityKey({ source: pollRun.source, metadata });
  const b = buildComparabilityKey({
    source: pollRun.source,
    metadata: { ...metadata, endpoint: "https://example.test/arcgis/MapServer/1" }
  });
  assert.notEqual(a, b);
});

test("query definition changes create a new comparison basis", () => {
  const a = buildComparabilityKey({ source: pollRun.source, metadata });
  const b = buildComparabilityKey({
    source: pollRun.source,
    metadata: { ...metadata, query_definition: "where=STATUS='ACTIVE'" }
  });
  assert.notEqual(a, b);
});

test("layer changes create a new comparison basis", () => {
  const a = buildComparabilityKey({ source: pollRun.source, metadata });
  const b = buildComparabilityKey({
    source: pollRun.source,
    metadata: { ...metadata, layer: "1" }
  });
  assert.notEqual(a, b);
});

test("coverage changes create a new comparison basis", () => {
  const a = buildComparabilityKey({ source: pollRun.source, metadata });
  const b = buildComparabilityKey({
    source: pollRun.source,
    metadata: { ...metadata, coverage_key: "sweden-full-v1" }
  });
  assert.notEqual(a, b);
});

test("schema changes create a new comparison basis", () => {
  const a = buildComparabilityKey({ source: pollRun.source, metadata });
  const b = buildComparabilityKey({
    source: pollRun.source,
    metadata: { ...metadata, schema_version: "2" }
  });
  assert.notEqual(a, b);
});

test("identity rule changes create a new comparison basis", () => {
  const a = buildComparabilityKey({ source: pollRun.source, metadata });
  const b = buildComparabilityKey({
    source: pollRun.source,
    metadata: { ...metadata, identity_version: "arcgis-globalid-v2" }
  });
  assert.notEqual(a, b);
});

test("missing endpoint or query definition is rejected", () => {
  for (const field of ["endpoint", "query_definition"]) {
    const r = mapWorkerScanToSnapshotEnvelope({
      pollRun,
      scanSession,
      metadata: { ...metadata, [field]: "" }
    });
    assert.equal(r.valid, false);
    assert.ok(r.errors.includes("metadata_missing_" + field));
  }
});

test("same comparison metadata produces the same key across runs", () => {
  const a = buildComparabilityKey({ source: pollRun.source, metadata });
  const b = buildComparabilityKey({ source: pollRun.source, metadata });
  assert.equal(a, b);
});
