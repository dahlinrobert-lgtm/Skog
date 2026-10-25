import { readFile } from "node:fs/promises";

function valueAt(report, path) {
  return path.split(".").reduce((value, key) => value?.[key], report);
}

function sampleIds(report) {
  const ids = valueAt(report, "checks.pagination.sample_ids");
  if (Array.isArray(ids)) return ids.map(String);
  const firstPage = valueAt(report, "checks.first_page.sample_ids");
  return Array.isArray(firstPage) ? firstPage.map(String) : [];
}

export function compareReports(older, newer) {
  const oldCount = valueAt(older, "checks.source_size.total_feature_count");
  const newCount = valueAt(newer, "checks.source_size.total_feature_count");
  const oldFingerprint = valueAt(older, "checks.repeatability_fingerprint.sha256") ?? null;
  const newFingerprint = valueAt(newer, "checks.repeatability_fingerprint.sha256") ?? null;
  const oldIds = new Set(sampleIds(older));
  const newIds = new Set(sampleIds(newer));
  const sharedIds = [...oldIds].filter(id => newIds.has(id));
  const oldLayer = valueAt(older, "checks.layer_metadata.objectIdField") ?? null;
  const newLayer = valueAt(newer, "checks.layer_metadata.objectIdField") ?? null;
  const oldNewest = valueAt(older, "checks.newest_records") ?? {};
  const newNewest = valueAt(newer, "checks.newest_records") ?? {};
  const warnings = [];

  if (typeof oldCount !== "number" || typeof newCount !== "number") {
    warnings.push("missing_source_count");
  } else if (oldCount !== newCount) {
    warnings.push("source_count_changed");
  }
  if (oldFingerprint && newFingerprint && oldFingerprint !== newFingerprint) {
    warnings.push("sample_fingerprint_changed");
  }
  if (oldLayer !== newLayer) warnings.push("technical_id_field_changed");
  if (oldIds.size && newIds.size && sharedIds.length === 0) {
    warnings.push("no_overlap_between_sampled_ids");
  }
  if (valueAt(newer, "checks.sample_integrity.ok") === false) {
    warnings.push("newer_sample_integrity_failed");
  }
  if (Array.isArray(newer.errors) && newer.errors.length) {
    warnings.push("newer_probe_has_errors");
  }

  return {
    older_checked_at: older.checked_at ?? null,
    newer_checked_at: newer.checked_at ?? null,
    elapsed_hours: older.checked_at && newer.checked_at
      ? Math.round((Date.parse(newer.checked_at) - Date.parse(older.checked_at)) / 36_000) / 100
      : null,
    source_count: { older: oldCount ?? null, newer: newCount ?? null,
      delta: typeof oldCount === "number" && typeof newCount === "number" ? newCount - oldCount : null },
    technical_id_field: { older: oldLayer, newer: newLayer, unchanged: oldLayer === newLayer },
    repeatability_fingerprint: { older: oldFingerprint, newer: newFingerprint,
      unchanged: oldFingerprint !== null && oldFingerprint === newFingerprint },
    sampled_id_overlap: { older_unique: oldIds.size, newer_unique: newIds.size,
      shared: sharedIds.length, older_only: [...oldIds].filter(id => !newIds.has(id)).length,
      newer_only: [...newIds].filter(id => !oldIds.has(id)).length },
    newest_records: {
      older_min_source_date: oldNewest.min_source_date_in_sample ?? null,
      older_max_source_date: oldNewest.max_source_date ?? null,
      newer_min_source_date: newNewest.min_source_date_in_sample ?? null,
      newer_max_source_date: newNewest.max_source_date ?? null,
      older_status_values: oldNewest.status_values ?? [],
      newer_status_values: newNewest.status_values ?? []
    },
    warnings,
    interpretation: "Diagnostic comparison only. Count or sample changes do not prove records were deleted, and matching samples do not prove a complete or transactionally consistent scan."
  };
}

async function main() {
  const [, , olderPath, newerPath] = process.argv;
  if (!olderPath || !newerPath) {
    console.error("Usage: node skogskoll/scripts/compare-probes.mjs <older-report.json> <newer-report.json>");
    process.exitCode = 2;
    return;
  }
  try {
    const [olderText, newerText] = await Promise.all([
      readFile(olderPath, "utf8"), readFile(newerPath, "utf8")
    ]);
    const older = JSON.parse(olderText);
    const newer = JSON.parse(newerText);
    console.log(JSON.stringify(compareReports(older, newer), null, 2));
  } catch (error) {
    console.error(String(error?.stack ?? error));
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  await main();
}
