/**
 * Pure helpers for validating ArcGIS offset-paginated scans.
 * This module does not perform network requests or persist records.
 */

export function collectPageDiagnostics(pages, idOf = feature => feature?.id ?? feature?.properties?.OBJECTID ?? null) {
  const normalizedPages = Array.isArray(pages) ? pages : [];
  const features = [];
  const ids = [];
  let missingIdCount = 0;
  let malformedPageCount = 0;

  for (const page of normalizedPages) {
    if (!Array.isArray(page?.features)) {
      malformedPageCount++;
      continue;
    }
    for (const feature of page.features) {
      features.push(feature);
      const rawId = idOf(feature);
      if (rawId === null || rawId === undefined || String(rawId).trim() === "") {
        missingIdCount++;
      } else {
        ids.push(String(rawId));
      }
    }
  }

  const uniqueIds = new Set(ids);
  return {
    pageCount: normalizedPages.length,
    fetchedCount: features.length,
    idCount: ids.length,
    uniqueIdCount: uniqueIds.size,
    duplicateIdCount: ids.length - uniqueIds.size,
    missingIdCount,
    malformedPageCount,
    hasTransferLimit: normalizedPages.some(page => page?.exceededTransferLimit === true),
    allPagesWellFormed: malformedPageCount === 0,
    noDuplicateIds: ids.length === uniqueIds.size,
    hasCompleteIdCoverage: missingIdCount === 0 && malformedPageCount === 0
  };
}

/**
 * Conservative guard before a caller uses a scan for reconciliation.
 * The service count must match the fetched count; pages must be well formed;
 * IDs must be present and unique; and no transfer-limit flag may remain.
 */
export function assessScanCompleteness({ diagnostics, reportedTotal, requestedPageSize }) {
  if (!diagnostics || !Number.isInteger(reportedTotal) || reportedTotal < 0) {
    return { complete: false, reasons: ["missing_or_invalid_count"] };
  }
  const reasons = [];
  if (!diagnostics.allPagesWellFormed) reasons.push("malformed_page");
  if (diagnostics.hasTransferLimit) reasons.push("transfer_limit_reported");
  if (!diagnostics.noDuplicateIds) reasons.push("duplicate_ids");
  if (!diagnostics.hasCompleteIdCoverage) reasons.push("missing_ids");
  if (diagnostics.fetchedCount !== reportedTotal) reasons.push("count_mismatch");
  if (!Number.isInteger(requestedPageSize) || requestedPageSize < 1) reasons.push("invalid_page_size");
  return { complete: reasons.length === 0, reasons };
}
