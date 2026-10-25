import test from "node:test";
import assert from "node:assert/strict";
import { compareReports } from "../scripts/compare-probes.mjs";

const report = (overrides = {}) => ({
  checked_at: "2026-10-25T00:00:00.000Z",
  errors: [],
  checks: {
    source_size: { total_feature_count: 1000 },
    layer_metadata: { objectIdField: "OBJECTID" },
    first_page: { sample_ids: [1, 2, 3] },
    repeatability_fingerprint: { sha256: "abc" },
    newest_records: {
      min_source_date_in_sample: "2026-10-20T00:00:00.000Z",
      max_source_date: "2026-10-24T00:00:00.000Z",
      status_values: ["Aktuell"]
    },
    sample_integrity: { ok: true }
  },
  ...overrides
});

test("matching reports compare cleanly and calculate elapsed hours", () => {
  const oldReport = report();
  const newReport = report({ checked_at: "2026-10-25T06:00:00.000Z" });
  const result = compareReports(oldReport, newReport);
  assert.equal(result.elapsed_hours, 6);
  assert.equal(result.source_count.delta, 0);
  assert.equal(result.repeatability_fingerprint.unchanged, true);
  assert.deepEqual(result.sampled_id_overlap, {
    older_unique: 3, newer_unique: 3, shared: 3, older_only: 0, newer_only: 0
  });
  assert.deepEqual(result.warnings, []);
});

test("count and fingerprint changes are flagged without claiming deletion", () => {
  const oldReport = report();
  const newer = report({
    checked_at: "2026-10-25T06:00:00.000Z",
    checks: {
      ...oldReport.checks,
      source_size: { total_feature_count: 998 },
      repeatability_fingerprint: { sha256: "different" },
      first_page: { sample_ids: [4, 5, 6] }
    }
  });
  const result = compareReports(oldReport, newer);
  assert.equal(result.source_count.delta, -2);
  assert.deepEqual(result.warnings, [
    "source_count_changed", "sample_fingerprint_changed", "no_overlap_between_sampled_ids"
  ]);
  assert.match(result.interpretation, /do not prove records were deleted/);
});

test("missing counts and a failed newer probe are reported", () => {
  const result = compareReports(report(), {
    checked_at: "2026-10-25T06:00:00.000Z",
    errors: ["probe failed"],
    checks: { sample_integrity: { ok: false }, layer_metadata: { objectIdField: "ROW_ID" } }
  });
  assert.equal(result.source_count.newer, null);
  assert.deepEqual(result.warnings, [
    "missing_source_count", "technical_id_field_changed",
    "newer_sample_integrity_failed", "newer_probe_has_errors"
  ]);
});
