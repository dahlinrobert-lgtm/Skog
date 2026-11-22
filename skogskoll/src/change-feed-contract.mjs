const REQUIRED = [
  "snapshot_id", "run_id", "source", "product", "layer", "captured_at",
  "status", "coverage_key", "schema_version", "identity_version"
];

function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validTime(value) {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

/**
 * Fail-closed comparison gate for immutable snapshot envelopes.
 * This function creates no disappearance events and performs no persistence.
 */
export function evaluateSnapshotPair(previous, current) {
  const reasons = [];
  for (const [label, snapshot] of [["previous", previous], ["current", current]]) {
    if (!snapshot || typeof snapshot !== "object") {
      reasons.push(label + "_snapshot_missing");
      continue;
    }
    for (const field of REQUIRED) {
      if (!nonEmpty(snapshot[field])) reasons.push(label + "_missing_" + field);
    }
    if (snapshot.status !== "complete") reasons.push(label + "_snapshot_not_complete");
    if (!validTime(snapshot.captured_at)) reasons.push(label + "_invalid_captured_at");
  }
  if (reasons.length) return { eligible: false, reasons: [...new Set(reasons)] };

  for (const field of ["source", "product", "layer", "coverage_key", "schema_version", "identity_version"]) {
    if (previous[field] !== current[field]) reasons.push("incompatible_" + field);
  }
  if (previous.snapshot_id === current.snapshot_id) reasons.push("snapshot_id_not_distinct");
  if (previous.run_id === current.run_id) reasons.push("run_id_not_distinct");
  if (Date.parse(current.captured_at) <= Date.parse(previous.captured_at)) reasons.push("current_snapshot_not_later");

  return { eligible: reasons.length === 0, reasons };
}

/**
 * Classify records only after a comparable pair has passed the gate.
 * A null previous snapshot is the silent first baseline.
 * Missing IDs in the current snapshot never become removal events.
 */
export function buildFeedEvents({ previousSnapshot, currentSnapshot, previousRecords = [], currentRecords = [] }) {
  if (!previousSnapshot) {
    return { eligible: currentSnapshot?.status === "complete", baseline: true, events: [], reasons: currentSnapshot?.status === "complete" ? [] : ["baseline_not_complete"] };
  }

  const gate = evaluateSnapshotPair(previousSnapshot, currentSnapshot);
  if (!gate.eligible) return { eligible: false, baseline: false, events: [], reasons: gate.reasons };

  const rightsApproved = currentSnapshot.customer_visibility === "approved" &&
    nonEmpty(currentSnapshot.rights_evidence_ref);
  if (!rightsApproved) {
    return { eligible: false, baseline: false, events: [], reasons: ["customer_visibility_not_approved_or_evidence_missing"] };
  }

  const prior = new Map();
  for (const record of previousRecords) {
    if (nonEmpty(record?.source_id)) prior.set(record.source_id, record);
  }

  const seen = new Set();
  const events = [];
  for (const record of currentRecords) {
    if (!nonEmpty(record?.source_id) || !nonEmpty(record?.content_hash)) continue;
    if (seen.has(record.source_id)) continue;
    seen.add(record.source_id);
    const before = prior.get(record.source_id);
    const event_type = !before ? "first_seen" :
      before.content_hash !== record.content_hash ? "changed" : null;
    if (!event_type) continue;
    events.push({
      event_type,
      detected_at: currentSnapshot.captured_at,
      source_event_at: record.source_event_at ?? null,
      source_published_at: record.source_published_at ?? null,
      snapshot_captured_at: currentSnapshot.captured_at,
      source: currentSnapshot.source,
      product: currentSnapshot.product,
      layer: currentSnapshot.layer,
      source_id: record.source_id,
      snapshot_id: currentSnapshot.snapshot_id,
      run_id: currentSnapshot.run_id,
      content_hash: record.content_hash,
      rights_evidence_ref: currentSnapshot.rights_evidence_ref
    });
  }
  return { eligible: true, baseline: false, events, reasons: [] };
}
