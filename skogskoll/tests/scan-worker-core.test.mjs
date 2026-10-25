import test from "node:test";
import assert from "node:assert/strict";
import { runScanBatch } from "../src/scan-worker-core.mjs";

function makeStore(total, initial = null) {
  let checkpoint = initial;
  const calls = { starts: 0, commits: [], finished: 0, failures: [] };
  return {
    calls,
    async loadCheckpoint() { return checkpoint; },
    async startScan({ sourceKey, reportedTotal, pageSize, checkpoint: start }) {
      calls.starts++;
      checkpoint = { ...start, scanId: "scan-1" };
      return "scan-1";
    },
    async commitPage({ nextCheckpoint }) {
      calls.commits.push(nextCheckpoint.fetchedCount);
      checkpoint = nextCheckpoint;
    },
    async finishScan() { calls.finished++; },
    async failScan(id, reason, details) { calls.failures.push({ id, reason, details }); }
  };
}
const feat = id => ({ type: "Feature", id, properties: { OBJECTID: id, Beteckn: `case-${id}` }, geometry: null });
function makeSource(total, ids = Array.from({ length: total }, (_, i) => i + 1)) {
  let countCalls = 0;
  return {
    key: "source",
    async getCount() { countCalls++; return typeof total === "function" ? total(countCalls) : total; },
    async getPage(offset, size) { return { features: ids.slice(offset, offset + size).map(feat) }; }
  };
}

test("worker commits a bounded batch and returns resumable progress", async () => {
  const store = makeStore(5);
  const result = await runScanBatch({ source: makeSource(5), store, pageSize: 2, maxPages: 1, observedAt: () => "2026-10-25T00:00:00Z" });
  assert.equal(result.status, "in_progress");
  assert.equal(result.fetchedCount, 2);
  assert.equal(result.nextOffset, 2);
  assert.deepEqual(store.calls.commits, [2]);
  assert.equal(store.calls.finished, 0);
});

test("worker resumes and only finishes after complete count coverage", async () => {
  const store = makeStore(3);
  const source = makeSource(3);
  const first = await runScanBatch({ source, store, pageSize: 2, maxPages: 1 });
  assert.equal(first.status, "in_progress");
  const second = await runScanBatch({ source, store, pageSize: 2, maxPages: 2 });
  assert.equal(second.status, "complete");
  assert.equal(second.fetchedCount, 3);
  assert.equal(store.calls.finished, 1);
  assert.deepEqual(store.calls.commits, [2, 3]);
});

test("worker aborts if source count changes during scan", async () => {
  const store = makeStore(3);
  let countCalls = 0;
  const source = {
    key: "source",
    async getCount() { countCalls++; return countCalls < 3 ? 3 : 4; },
    async getPage(offset, size) { return { features: [feat(1), feat(2)].slice(0, size) }; }
  };
  await assert.rejects(runScanBatch({ source, store, pageSize: 2, maxPages: 2 }), /source_count_changed/);
  assert.equal(store.calls.finished, 0);
  assert.equal(store.calls.failures.length, 1);
});

test("worker refuses malformed or ID-incomplete pages without committing", async () => {
  const store = makeStore(1);
  const source = {
    key: "source",
    async getCount() { return 1; },
    async getPage() { return { features: [{ type: "Feature", properties: {} }] }; }
  };
  await assert.rejects(runScanBatch({ source, store, pageSize: 1, maxPages: 1 }), /missing source ID/);
  assert.equal(store.calls.commits.length, 0);
  assert.equal(store.calls.finished, 0);
});

test("worker stops cleanly when max pages per run is reached", async () => {
  const store = makeStore(10);
  const result = await runScanBatch({ source: makeSource(10), store, pageSize: 2, maxPages: 2 });
  assert.equal(result.status, "in_progress");
  assert.equal(result.pagesFetched, 2);
  assert.equal(result.nextOffset, 4);
});

test("transient source failures preserve the committed scan for resumption", async () => {
  const store = makeStore(3);
  const source = {
    key: "source",
    async getCount() { return 3; },
    async getPage() { throw new Error("temporary fetch failed"); }
  };
  await assert.rejects(runScanBatch({ source, store, pageSize: 2, maxPages: 1 }), /temporary fetch failed/);
  assert.equal(store.calls.failures.length, 0);
  assert.equal(store.calls.finished, 0);
});
