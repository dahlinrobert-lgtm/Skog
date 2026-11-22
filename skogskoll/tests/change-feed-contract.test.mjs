import test from "node:test";
import assert from "node:assert/strict";
import { buildFeedEvents, evaluateSnapshotPair } from "../src/change-feed-contract.mjs";

const previous = {
  snapshot_id: "snap-1", run_id: "run-1", source: "source-a", product: "product-a",
  layer: "layer-a", captured_at: "2026-11-20T10:00:00Z", status: "complete",
  coverage_key: "coverage-v1", schema_version: "1", identity_version: "1",
  customer_visibility: "approved", rights_evidence_ref: "docs/evidence.md"
};
const current = { ...previous, snapshot_id: "snap-2", run_id: "run-2", captured_at: "2026-11-21T10:00:00Z" };

test("only complete snapshots with identical scope and versions are comparable", () => {
  assert.equal(evaluateSnapshotPair(previous, current).eligible, true);
  for (const patch of [
    { status: "partial" }, { source: "other" }, { product: "other" },
    { layer: "other" }, { coverage_key: "changed" }, { schema_version: "2" },
    { identity_version: "2" }, { snapshot_id: previous.snapshot_id },
    { run_id: previous.run_id }, { captured_at: previous.captured_at }
  ]) assert.equal(evaluateSnapshotPair(previous, { ...current, ...patch }).eligible, false);
});

test("first complete baseline is silent", () => {
  const result = buildFeedEvents({ previousSnapshot: null, currentSnapshot: current, currentRecords: [{ source_id: "A", content_hash: "h1" }] });
  assert.equal(result.baseline, true);
  assert.deepEqual(result.events, []);
});

test("partial or failed snapshots cannot create events", () => {
  const result = buildFeedEvents({ previousSnapshot: { ...previous }, currentSnapshot: { ...current, status: "partial" }, previousRecords: [], currentRecords: [{ source_id: "B", content_hash: "h2" }] });
  assert.equal(result.eligible, false);
  assert.deepEqual(result.events, []);
});

test("rights gate fails closed even for technically comparable snapshots", () => {
  const result = buildFeedEvents({ previousSnapshot: previous, currentSnapshot: { ...current, customer_visibility: "pending", rights_evidence_ref: null }, previousRecords: [], currentRecords: [{ source_id: "B", content_hash: "h2" }] });
  assert.equal(result.eligible, false);
  assert.deepEqual(result.events, []);
});

test("new and changed records become events; unchanged records do not", () => {
  const result = buildFeedEvents({
    previousSnapshot: previous, currentSnapshot: current,
    previousRecords: [{ source_id: "A", content_hash: "old" }, { source_id: "B", content_hash: "same" }],
    currentRecords: [
      { source_id: "A", content_hash: "new" },
      { source_id: "B", content_hash: "same" },
      { source_id: "C", content_hash: "first" }
    ]
  });
  assert.equal(result.eligible, true);
  assert.deepEqual(result.events.map(event => [event.source_id, event.event_type]), [["A", "changed"], ["C", "first_seen"]]);
  assert.equal(result.events[0].detected_at, current.captured_at);
  assert.equal(result.events[0].source_event_at, null);
  assert.equal(result.events[0].rights_evidence_ref, "docs/evidence.md");
});

test("absence from current snapshot never creates a removal event", () => {
  const result = buildFeedEvents({ previousSnapshot: previous, currentSnapshot: current, previousRecords: [{ source_id: "gone", content_hash: "h" }], currentRecords: [] });
  assert.deepEqual(result.events, []);
});

test("missing record IDs or hashes are ignored rather than assigned invented identities", () => {
  const result = buildFeedEvents({ previousSnapshot: previous, currentSnapshot: current, currentRecords: [{ content_hash: "h" }, { source_id: "id" }] });
  assert.deepEqual(result.events, []);
});
