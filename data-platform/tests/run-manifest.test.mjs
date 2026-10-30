import test from "node:test";
import assert from "node:assert/strict";
import { createRunManifest, finalizeRunManifest, hashPayload, validateRunManifest } from "../src/run-manifest.mjs";

const startedAt = "2026-10-30T12:00:00.000Z";

test("creates a deterministic-shape manifest with no publication by default", () => {
  const manifest = createRunManifest({ sourceId: "sakfraga.decisions", runId: "run-1", startedAt });
  assert.equal(manifest.status, "running");
  assert.equal(manifest.output.published, false);
  assert.deepEqual(manifest.counts, { fetched: 0, inserted: 0, updated: 0, unchanged: 0, rejected: 0 });
  assert.deepEqual(validateRunManifest(manifest), []);
});

test("successful run can publish only when explicitly requested", () => {
  const manifest = createRunManifest({ sourceId: "sakfraga.decisions", runId: "run-2", startedAt });
  const completed = finalizeRunManifest(manifest, {
    status: "success",
    finishedAt: "2026-10-30T12:01:00.000Z",
    output: { published: true, dataset_version: "v1" }
  });
  assert.equal(completed.output.published, true);
  assert.deepEqual(validateRunManifest(completed), []);
});

test("failed or warning runs cannot publish", () => {
  const manifest = createRunManifest({ sourceId: "sakfraga.decisions", runId: "run-3", startedAt });
  const failed = finalizeRunManifest(manifest, { status: "failed", error: "timeout" });
  assert.equal(failed.output.published, false);
  assert.match(validateRunManifest({ ...failed, output: { ...failed.output, published: true } }).join(" "), /only successful runs/);
});

test("failed run requires an error", () => {
  const manifest = createRunManifest({ sourceId: "sakfraga.decisions", runId: "run-4", startedAt });
  assert.throws(() => finalizeRunManifest(manifest, { status: "failed" }), /Invalid run manifest/);
});

test("rejects negative and non-integer counters", () => {
  const manifest = createRunManifest({ sourceId: "sakfraga.decisions", runId: "run-5", startedAt });
  assert.match(validateRunManifest({ ...manifest, counts: { ...manifest.counts, fetched: -1 } }).join(" "), /non-negative integer/);
  assert.match(validateRunManifest({ ...manifest, counts: { ...manifest.counts, fetched: 1.2 } }).join(" "), /non-negative integer/);
});

test("payload hash is stable for equivalent serialized payloads", () => {
  assert.equal(hashPayload({ a: 1, b: 2 }), hashPayload(JSON.stringify({ a: 1, b: 2 })));
});
