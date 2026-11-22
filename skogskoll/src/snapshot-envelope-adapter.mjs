const REQUIRED_METADATA = ["product", "layer", "coverage_key", "schema_version", "identity_version"];
const nonEmpty = value => typeof value === "string" && value.trim().length > 0;
const validTime = value => typeof value === "string" && Number.isFinite(Date.parse(value));

/** Pure mapping from existing worker run/scan rows to the neutral snapshot envelope. */
export function mapWorkerScanToSnapshotEnvelope({ pollRun, scanSession, metadata }) {
  const errors = [];
  if (!pollRun || typeof pollRun !== "object") errors.push("poll_run_missing");
  if (!scanSession || typeof scanSession !== "object") errors.push("scan_session_missing");
  if (!metadata || typeof metadata !== "object") errors.push("snapshot_metadata_missing");
  if (errors.length) return { valid: false, errors, envelope: null };
  for (const field of REQUIRED_METADATA) if (!nonEmpty(metadata[field])) errors.push("metadata_missing_" + field);
  if (!nonEmpty(pollRun.id)) errors.push("poll_run_id_missing");
  if (!nonEmpty(pollRun.source)) errors.push("poll_run_source_missing");
  if (!nonEmpty(scanSession.id)) errors.push("scan_session_id_missing");
  if (pollRun.source !== scanSession.source) errors.push("source_mismatch");
  const total = scanSession.source_count, fetched = scanSession.fetched_count, offset = scanSession.next_offset;
  const countsValid = Number.isSafeInteger(total) && total >= 0 && Number.isSafeInteger(fetched) && fetched >= 0 && Number.isSafeInteger(offset) && offset >= 0;
  if (!countsValid) errors.push("scan_counts_invalid");
  const complete = countsValid && scanSession.status === "complete" && pollRun.status === "success" && fetched === total && offset === total && pollRun.fetched_count === total && validTime(scanSession.completed_at) && validTime(pollRun.finished_at);
  const failed = scanSession.status === "failed" || scanSession.status === "abandoned" || pollRun.status === "failed";
  const status = complete ? "complete" : failed ? "failed" : "partial";
  const capturedAt = scanSession.completed_at ?? pollRun.finished_at ?? null;
  if (!validTime(capturedAt)) errors.push("captured_at_unavailable");
  const reasons = complete ? [] : [
    ...(scanSession.status !== "complete" ? ["scan_not_complete"] : []),
    ...(pollRun.status !== "success" ? ["poll_run_not_success"] : []),
    ...(fetched !== total ? ["scan_count_mismatch"] : []),
    ...(offset !== total ? ["scan_offset_mismatch"] : []),
    ...(pollRun.fetched_count !== total ? ["poll_run_count_mismatch"] : []),
    ...(!validTime(scanSession.completed_at) ? ["scan_completion_time_missing"] : []),
    ...(!validTime(pollRun.finished_at) ? ["poll_run_finish_time_missing"] : [])
  ];
  const envelope = {
    snapshot_id: nonEmpty(pollRun.id) && nonEmpty(scanSession.id) ? "skogskoll-worker:" + pollRun.id + ":" + scanSession.id : null,
    run_id: nonEmpty(pollRun.id) ? pollRun.id : null,
    source: nonEmpty(pollRun.source) ? pollRun.source : null,
    product: metadata.product ?? null, layer: metadata.layer ?? null, captured_at: capturedAt,
    status, coverage_key: metadata.coverage_key ?? null, schema_version: metadata.schema_version ?? null,
    identity_version: metadata.identity_version ?? null,
    customer_visibility: metadata.customer_visibility ?? "not_assessed",
    rights_evidence_ref: metadata.rights_evidence_ref ?? null,
    diagnostics: { scan_session_id: scanSession.id, scan_status: scanSession.status ?? null,
      poll_run_status: pollRun.status ?? null, source_count: countsValid ? total : null,
      fetched_count: countsValid ? fetched : null, next_offset: countsValid ? offset : null,
      poll_run_fetched_count: Number.isSafeInteger(pollRun.fetched_count) ? pollRun.fetched_count : null,
      completeness_reasons: reasons }
  };
  return { valid: errors.length === 0, errors, envelope };
}
