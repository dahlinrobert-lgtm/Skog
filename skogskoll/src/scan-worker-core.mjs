import { advanceCheckpoint, createCheckpoint, validateCheckpoint } from "./scan-plan.mjs";
import { normalizeFeature, SOURCE_ID } from "./observation-core.mjs";

function isFatalScanError(error) {
  const message = String(error?.message ?? error).toLowerCase();
  // Network/server failures can be retried from the last atomically committed
  // page. Integrity and snapshot violations must stop this session.
  if (message.includes("stale checkpoint")) return false;
  if (/^supabase rest 4\d\d:/.test(message)) return true;
  return [
    "source returned an invalid count",
    "source_count_changed:",
    "source_count_changed_at_finish:",
    "source returned a malformed page",
    "source returned an invalid count",
    "arcgis returned invalid count",
    "arcgis returned invalid json",
    "arcgis page omitted features array",
    "missing source id",
    "duplicate id",
    "transfer limit reported",
    "empty page before reported total",
    "page exceeds requested page size",
    "page exceeds source total",
    "source id; do not advance",
    "persisted checkpoint",
    "no object id field",
    "invalid geojson",
    "geometry"
  ].some(fragment => message.includes(fragment));
}

/**
 * Executes one bounded scan batch against injected source/store adapters.
 * The store must commit records, seen IDs and the next checkpoint atomically in
 * commitPage(). This orchestration layer deliberately sends no alerts.
 */
export async function runScanBatch({
  source,
  store,
  pageSize = 500,
  maxPages = 50,
  mode = "baseline",
  observedAt = () => new Date().toISOString()
}) {
  if (!source || typeof source.getCount !== "function" || typeof source.getPage !== "function") {
    throw new TypeError("source adapter must provide getCount() and getPage(offset, pageSize)");
  }
  if (!store || typeof store.loadCheckpoint !== "function" || typeof store.startScan !== "function" ||
      typeof store.commitPage !== "function" || typeof store.finishScan !== "function" ||
      typeof store.failScan !== "function") {
    throw new TypeError("store adapter must provide loadCheckpoint, startScan, commitPage, finishScan and failScan");
  }
  if (!Number.isSafeInteger(pageSize) || pageSize < 1) throw new TypeError("pageSize must be positive");
  if (!Number.isSafeInteger(maxPages) || maxPages < 1) throw new TypeError("maxPages must be positive");

  const sourceKey = source.key ?? SOURCE_ID;
  let scanId = null;
  try {
    const reportedTotal = await source.getCount();
    if (!Number.isSafeInteger(reportedTotal) || reportedTotal < 0) {
      throw new Error("source returned an invalid count");
    }

    let checkpoint = await store.loadCheckpoint(sourceKey);
    if (checkpoint) {
      const validation = validateCheckpoint(checkpoint, { sourceKey, reportedTotal, pageSize });
      if (!validation.valid) {
        await store.failScan(checkpoint.scanId ?? null, "checkpoint_invalid", { reasons: validation.reasons });
        checkpoint = null;
      }
    }
    if (!checkpoint) {
      checkpoint = createCheckpoint({ sourceKey, reportedTotal, pageSize, externalSeenIds: store.externalSeenIds === true });
      scanId = await store.startScan({ sourceKey, reportedTotal, pageSize, checkpoint, mode });
      checkpoint = { ...checkpoint, scanId };
    } else {
      scanId = checkpoint.scanId ?? null;
    }

    if (checkpoint.complete) {
      await store.finishScan(scanId, checkpoint);
      return { status: "complete", scanId, fetchedCount: checkpoint.fetchedCount, pagesFetched: 0 };
    }

    let pagesFetched = 0;
    while (pagesFetched < maxPages && !checkpoint.complete) {
      // Re-read count before every page: never mix a changed source snapshot into one scan.
      const currentCount = await source.getCount();
      if (currentCount !== reportedTotal) {
        throw new Error(`source_count_changed:${reportedTotal}->${currentCount}`);
      }
      const page = await source.getPage(checkpoint.nextOffset, pageSize);
      if (!page || !Array.isArray(page.features)) throw new Error("source returned a malformed page");
      const next = advanceCheckpoint(checkpoint, page, { observedAt: observedAt() });
      const records = page.features.map(feature => normalizeFeature(feature, next.updatedAt));
      if (records.some(record => !record.ok)) throw new Error("page contains a feature without a stable source ID");

      // Atomic adapter contract: upsert observations + append history + insert seen IDs + checkpoint.
      await store.commitPage({
        scanId,
        previousCheckpoint: checkpoint,
        nextCheckpoint: next,
        records,
        rawFeatures: page.features,
        // The persistent store keeps IDs normalized in its own table, not in
        // the checkpoint JSON. The SQL RPC validates the IDs and commits them
        // with the observations and offsets in one transaction.
        pageIds: records.map(record => record.source_id)
      });
      checkpoint = { ...next, scanId };
      pagesFetched++;
    }

    if (checkpoint.complete) {
      // Final independent count check before a scan is allowed to be marked complete.
      const finalCount = await source.getCount();
      if (finalCount !== reportedTotal) throw new Error(`source_count_changed_at_finish:${reportedTotal}->${finalCount}`);
      await store.finishScan(scanId, checkpoint);
      return { status: "complete", scanId, fetchedCount: checkpoint.fetchedCount, pagesFetched };
    }
    return { status: "in_progress", scanId, fetchedCount: checkpoint.fetchedCount, pagesFetched, nextOffset: checkpoint.nextOffset };
  } catch (error) {
    // Preserve the last committed checkpoint after transient network/5xx errors.
    // Structural source errors and known data-integrity violations are terminal
    // for this scan and must be recorded as failed rather than retried forever.
    if (scanId && isFatalScanError(error)) {
      await store.failScan(scanId, String(error?.message ?? error), { sourceKey }).catch(() => {});
    }
    throw error;
  }
}
