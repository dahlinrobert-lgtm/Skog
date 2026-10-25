import test from "node:test";
import assert from "node:assert/strict";
import { advanceCheckpoint, createCheckpoint, createScanPlan, validateCheckpoint } from "../src/scan-plan.mjs";

const feature = id => ({ type: "Feature", id, properties: { OBJECTID: id } });

test("scan plan estimates bounded runs without loading the whole layer", () => {
  assert.deepEqual(createScanPlan({ reportedTotal: 129733, pageSize: 500, maxPagesPerRun: 50 }), {
    reportedTotal: 129733, pageSize: 500, maxPagesPerRun: 50, expectedPageCount: 260, plannedRunCount: 6
  });
});

test("checkpoint validation rejects changed source count", () => {
  const checkpoint = createCheckpoint({ sourceKey: "skogsstyrelsen:avverkningsanmalan", reportedTotal: 3, pageSize: 2 });
  assert.deepEqual(validateCheckpoint(checkpoint, {
    sourceKey: "skogsstyrelsen:avverkningsanmalan", reportedTotal: 4, pageSize: 2
  }), { valid: false, reasons: ["source_count_changed"] });
});

test("checkpoint advances only with complete page data", () => {
  const start = createCheckpoint({ sourceKey: "source", reportedTotal: 3, pageSize: 2 });
  const one = advanceCheckpoint(start, { features: [feature(1), feature(2)] }, { observedAt: "2026-10-25T00:00:00Z" });
  assert.equal(one.nextOffset, 2);
  assert.equal(one.fetchedCount, 2);
  assert.equal(one.complete, false);
  const two = advanceCheckpoint(one, { features: [feature(3)] });
  assert.equal(two.nextOffset, 3);
  assert.equal(two.fetchedCount, 3);
  assert.equal(two.complete, true);
});

test("checkpoint does not advance on transfer limit, missing ID, or duplicate ID", () => {
  const start = createCheckpoint({ sourceKey: "source", reportedTotal: 3, pageSize: 2 });
  assert.throws(() => advanceCheckpoint(start, { features: [feature(1)], exceededTransferLimit: true }), /transfer limit/);
  assert.throws(() => advanceCheckpoint(start, { features: [{ properties: {} }] }), /missing source ID/);
  const one = advanceCheckpoint(start, { features: [feature(1)] });
  assert.throws(() => advanceCheckpoint(one, { features: [feature(1)] }), /duplicate ID across pages/);
});

test("checkpoint rejects empty page before reported total and oversize page", () => {
  const start = createCheckpoint({ sourceKey: "source", reportedTotal: 3, pageSize: 2 });
  assert.throws(() => advanceCheckpoint(start, { features: [] }), /empty page/);
  assert.throws(() => advanceCheckpoint(start, { features: [feature(1), feature(2), feature(3)] }), /exceeds requested page size/);
});

test("checkpoint refuses changed page size and cannot advance once complete", () => {
  const start = createCheckpoint({ sourceKey: "source", reportedTotal: 1, pageSize: 1 });
  assert.equal(validateCheckpoint(start, { sourceKey: "source", reportedTotal: 1, pageSize: 2 }).valid, false);
  const done = advanceCheckpoint(start, { features: [feature(1)] });
  assert.equal(done.complete, true);
  assert.throws(() => advanceCheckpoint(done, { features: [] }), /already complete/);
});
