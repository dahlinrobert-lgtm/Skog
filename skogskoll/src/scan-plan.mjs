/**
 * Deterministic scan planning for ArcGIS offset pagination.
 * The caller persists checkpoints; this module performs no I/O.
 */

export function createScanPlan({ reportedTotal, pageSize = 500, maxPagesPerRun = 50 }) {
  if (!Number.isSafeInteger(reportedTotal) || reportedTotal < 0) {
    throw new TypeError("reportedTotal must be a non-negative safe integer");
  }
  if (!Number.isSafeInteger(pageSize) || pageSize < 1) {
    throw new TypeError("pageSize must be a positive safe integer");
  }
  if (!Number.isSafeInteger(maxPagesPerRun) || maxPagesPerRun < 1) {
    throw new TypeError("maxPagesPerRun must be a positive safe integer");
  }
  return {
    reportedTotal,
    pageSize,
    maxPagesPerRun,
    expectedPageCount: Math.ceil(reportedTotal / pageSize),
    plannedRunCount: Math.ceil(Math.ceil(reportedTotal / pageSize) / maxPagesPerRun)
  };
}

export function createCheckpoint({ sourceKey, reportedTotal, pageSize, nextOffset = 0, fetchedCount = 0, seenIds = [] }) {
  if (!sourceKey || typeof sourceKey !== "string") throw new TypeError("sourceKey is required");
  for (const [name, value] of Object.entries({ reportedTotal, pageSize, nextOffset, fetchedCount })) {
    if (!Number.isSafeInteger(value) || value < 0) throw new TypeError(name + " must be a non-negative safe integer");
  }
  if (pageSize < 1) throw new TypeError("pageSize must be positive");
  if (nextOffset > reportedTotal) throw new RangeError("nextOffset cannot exceed reportedTotal");
  if (fetchedCount > reportedTotal) throw new RangeError("fetchedCount cannot exceed reportedTotal");
  if (!Array.isArray(seenIds)) throw new TypeError("seenIds must be an array");
  const ids = seenIds.map(String);
  if (new Set(ids).size !== ids.length) throw new Error("seenIds must be unique");
  if (ids.length !== fetchedCount) throw new Error("seenIds length must equal fetchedCount");
  if (nextOffset !== fetchedCount) throw new Error("nextOffset must equal fetchedCount");
  return {
    schemaVersion: 1,
    sourceKey,
    reportedTotal,
    pageSize,
    nextOffset,
    fetchedCount,
    // Keep the pure planning API self-contained; production stores can load
    // normalized IDs from scan_seen_ids and omit this in the persisted JSON.
    seenIds: [...new Set(ids)],
    updatedAt: null,
    complete: reportedTotal === 0
  };
}

export function validateCheckpoint(checkpoint, { sourceKey, reportedTotal, pageSize }) {
  const reasons = [];
  if (!checkpoint || checkpoint.schemaVersion !== 1) reasons.push("unsupported_checkpoint_schema");
  if (checkpoint?.sourceKey !== sourceKey) reasons.push("source_mismatch");
  if (checkpoint?.reportedTotal !== reportedTotal) reasons.push("source_count_changed");
  if (checkpoint?.pageSize !== pageSize) reasons.push("page_size_changed");
  if (!Number.isSafeInteger(checkpoint?.nextOffset) || checkpoint.nextOffset < 0) reasons.push("invalid_next_offset");
  if (!Number.isSafeInteger(checkpoint?.fetchedCount) || checkpoint.fetchedCount < 0) reasons.push("invalid_fetched_count");
  if (checkpoint?.nextOffset > reportedTotal) reasons.push("offset_exceeds_total");
  if (checkpoint?.fetchedCount > reportedTotal) reasons.push("fetched_exceeds_total");
  if (checkpoint?.nextOffset !== checkpoint?.fetchedCount) reasons.push("offset_count_mismatch");
  if (!Array.isArray(checkpoint?.seenIds)) {
    reasons.push("invalid_seen_ids");
  } else {
    if (new Set(checkpoint.seenIds.map(String)).size !== checkpoint.seenIds.length) reasons.push("duplicate_checkpoint_ids");
    if (checkpoint.seenIds.length !== checkpoint.fetchedCount) reasons.push("checkpoint_id_count_mismatch");
  }
  if (checkpoint?.complete !== (checkpoint?.nextOffset === reportedTotal && checkpoint?.fetchedCount === reportedTotal)) {
    reasons.push("completion_state_mismatch");
  }
  return { valid: reasons.length === 0, reasons };
}

export function advanceCheckpoint(checkpoint, page, { idOf = feature => feature?.id ?? feature?.properties?.OBJECTID ?? null, observedAt = new Date().toISOString() } = {}) {
  if (!checkpoint || checkpoint.complete) throw new Error("checkpoint is missing or already complete");
  if (!Array.isArray(page?.features)) throw new TypeError("page.features must be an array");
  if (page.exceededTransferLimit === true) throw new Error("transfer limit reported; do not advance checkpoint");
  if (page.features.length === 0 && checkpoint.nextOffset < checkpoint.reportedTotal) {
    throw new Error("empty page before reported total; scan cannot be completed");
  }
  if (page.features.length > checkpoint.pageSize) throw new Error("page exceeds requested page size");

  const existing = new Set(checkpoint.seenIds);
  const pageIds = [];
  for (const feature of page.features) {
    const id = idOf(feature);
    if (id === null || id === undefined || String(id).trim() === "") {
      throw new Error("missing source ID; do not advance checkpoint");
    }
    pageIds.push(String(id));
  }
  if (new Set(pageIds).size !== pageIds.length) throw new Error("duplicate IDs within page; do not advance checkpoint");
  if (pageIds.some(id => existing.has(id))) throw new Error("duplicate ID across pages; do not advance checkpoint");

  const nextOffset = checkpoint.nextOffset + page.features.length;
  const fetchedCount = checkpoint.fetchedCount + page.features.length;
  if (nextOffset > checkpoint.reportedTotal || fetchedCount > checkpoint.reportedTotal) {
    throw new Error("page exceeds source total; do not advance checkpoint");
  }
  const complete = nextOffset === checkpoint.reportedTotal && fetchedCount === checkpoint.reportedTotal;
  return {
    ...checkpoint,
    nextOffset,
    fetchedCount,
    seenIds: [...checkpoint.seenIds, ...pageIds],
    updatedAt: observedAt,
    complete
  };
}
