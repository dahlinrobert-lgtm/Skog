import { createHash, randomUUID } from "node:crypto";

const STATUSES = new Set(["running", "success", "warning", "failed"]);
const COUNT_FIELDS = ["fetched", "inserted", "updated", "unchanged", "rejected"];

function isIsoDate(value) {
  return typeof value === "string" && !Number.isNaN(Date.parse(value)) && /^\\d{4}-\\d{2}-\\d{2}T/.test(value);
}

export function createRunManifest({
  sourceId,
  scope = {},
  startedAt = new Date().toISOString(),
  runId = randomUUID(),
  sourceSnapshot = null
} = {}) {
  if (typeof sourceId !== "string" || !sourceId.trim()) throw new TypeError("sourceId is required");
  if (!isIsoDate(startedAt)) throw new TypeError("startedAt must be an ISO datetime");
  return {
    schema_version: 1,
    run_id: runId,
    source_id: sourceId,
    started_at: startedAt,
    status: "running",
    scope,
    source_snapshot: sourceSnapshot,
    checkpoint: null,
    counts: { fetched: 0, inserted: 0, updated: 0, unchanged: 0, rejected: 0 },
    output: { published: false, dataset_version: null, manifest_uri: null },
    diagnostics: [],
    error: null
  };
}

export function updateRunManifest(manifest, patch = {}) {
  const next = structuredClone(manifest);
  if (patch.counts) next.counts = { ...next.counts, ...patch.counts };
  for (const key of ["status", "finished_at", "checkpoint", "source_snapshot", "diagnostics", "error"]) {
    if (Object.hasOwn(patch, key)) next[key] = patch[key];
  }
  if (patch.output) next.output = { ...next.output, ...patch.output };
  const errors = validateRunManifest(next);
  if (errors.length) throw new TypeError("Invalid run manifest: " + errors.join("; "));
  return next;
}

export function validateRunManifest(value) {
  const errors = [];
  if (!value || typeof value !== "object" || Array.isArray(value)) return ["manifest must be an object"];
  if (value.schema_version !== 1) errors.push("schema_version must be 1");
  for (const key of ["run_id", "source_id"]) if (typeof value[key] !== "string" || !value[key].trim()) errors.push(key + " is required");
  if (!isIsoDate(value.started_at)) errors.push("started_at must be an ISO datetime");
  if (value.finished_at != null && !isIsoDate(value.finished_at)) errors.push("finished_at must be an ISO datetime");
  if (!STATUSES.has(value.status)) errors.push("status is invalid");
  if (!value.scope || typeof value.scope !== "object" || Array.isArray(value.scope)) errors.push("scope must be an object");
  if (!value.counts || typeof value.counts !== "object") errors.push("counts is required");
  else for (const key of COUNT_FIELDS) if (!Number.isSafeInteger(value.counts[key]) || value.counts[key] < 0) errors.push("counts." + key + " must be a non-negative integer");
  if (!value.output || typeof value.output.published !== "boolean") errors.push("output.published must be boolean");
  if (value.status === "success" && !value.finished_at) errors.push("successful run requires finished_at");
  if (value.status !== "success" && value.output?.published) errors.push("only successful runs may publish output");
  if (value.status === "failed" && !value.error) errors.push("failed run requires an error");
  return errors;
}

export function finalizeRunManifest(manifest, {
  status,
  finishedAt = new Date().toISOString(),
  output = {},
  error = null,
  diagnostics
} = {}) {
  if (!STATUSES.has(status) || status === "running") throw new TypeError("final status must be success, warning or failed");
  const next = updateRunManifest(manifest, {
    status,
    finished_at: finishedAt,
    output: { ...output, published: status === "success" && output.published === true },
    error,
    ...(diagnostics ? { diagnostics } : {})
  });
  return next;
}

export function hashPayload(value) {
  return createHash("sha256").update(typeof value === "string" ? value : JSON.stringify(value)).digest("hex");
}
