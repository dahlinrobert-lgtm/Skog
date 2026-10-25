import test from "node:test";
import assert from "node:assert/strict";
import { assessScanCompleteness, collectPageDiagnostics } from "../src/pagination-core.mjs";

const page = (ids, exceededTransferLimit = false) => ({
  features: ids.map(id => ({ type: "Feature", id, properties: { OBJECTID: id } })),
  exceededTransferLimit
});

test("complete scan requires agreement with source count and unique IDs", () => {
  const diagnostics = collectPageDiagnostics([page([1, 2]), page([3])]);
  assert.equal(diagnostics.fetchedCount, 3);
  assert.equal(diagnostics.uniqueIdCount, 3);
  assert.deepEqual(assessScanCompleteness({
    diagnostics, reportedTotal: 3, requestedPageSize: 2
  }), { complete: true, reasons: [] });
});

test("bounded probe cannot be mistaken for a complete scan", () => {
  const diagnostics = collectPageDiagnostics([page([1, 2, 3])]);
  assert.deepEqual(assessScanCompleteness({
    diagnostics, reportedTotal: 129735, requestedPageSize: 100
  }), { complete: false, reasons: ["count_mismatch"] });
});

test("transfer limit and duplicate IDs fail the completeness guard", () => {
  const diagnostics = collectPageDiagnostics([page([1, 2], true), page([2, 3])]);
  assert.deepEqual(assessScanCompleteness({
    diagnostics, reportedTotal: 4, requestedPageSize: 2
  }), { complete: false, reasons: ["transfer_limit_reported", "duplicate_ids"] });
});

test("missing IDs and malformed pages are surfaced", () => {
  const diagnostics = collectPageDiagnostics([
    { features: [{ properties: { OBJECTID: 1 } }, { properties: {} }] },
    { nope: true }
  ]);
  assert.equal(diagnostics.missingIdCount, 1);
  assert.equal(diagnostics.malformedPageCount, 1);
  assert.deepEqual(assessScanCompleteness({
    diagnostics, reportedTotal: 2, requestedPageSize: 100
  }), { complete: false, reasons: ["malformed_page", "missing_ids"] });
});

test("empty source can be complete when the valid count is zero", () => {
  const diagnostics = collectPageDiagnostics([{ features: [], exceededTransferLimit: false }]);
  assert.deepEqual(assessScanCompleteness({
    diagnostics, reportedTotal: 0, requestedPageSize: 100
  }), { complete: true, reasons: [] });
});

test("an invalid page size never passes completeness guard", () => {
  const diagnostics = collectPageDiagnostics([page([1])]);
  assert.deepEqual(assessScanCompleteness({
    diagnostics, reportedTotal: 1, requestedPageSize: 0
  }), { complete: false, reasons: ["invalid_page_size"] });
});
