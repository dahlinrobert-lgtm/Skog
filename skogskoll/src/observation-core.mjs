import { createHash } from "node:crypto";

export const SOURCE_ID = "skogsstyrelsen:avverkningsanmalan";

export function getStableSourceId(feature) {
  const properties = feature?.properties ?? {};
  const value = feature?.id ?? properties.OBJECTID ?? properties.ObjectId ?? properties.objectid;
  if (value === null || value === undefined || String(value).trim() === "") return null;
  return String(value);
}
export function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonicalize(value[key])]));
  return value;
}
export function contentHash(feature) {
  return createHash("sha256").update(JSON.stringify(canonicalize({properties: feature?.properties ?? {}, geometry: feature?.geometry ?? null}))).digest("hex");
}
export function normalizeFeature(feature, observedAt = new Date().toISOString()) {
  const sourceId = getStableSourceId(feature);
  if (!sourceId) return {ok:false,reason:"missing_stable_source_id"};
  const props = feature.properties ?? {};
  // Keep the source's received date distinct from the time our system first observed it.
  const sourceReceivedAt = props.Inkomdatum ?? props.InkomDatum ?? null;
  return {
    ok:true,
    source:SOURCE_ID,
    source_id:sourceId,
    observed_at:observedAt,
    source_received_at:sourceReceivedAt,
    // Backward-compatible alias; do not interpret this as publication/first-seen time.
    source_created_at:sourceReceivedAt,
    attributes:props,
    geometry:feature.geometry ?? null,
    content_hash:contentHash(feature)
  };
}
export function classifyObservation(current, previous) {
  if (!current?.ok) return {action:"reject",reason:current?.reason ?? "invalid_observation"};
  if (!previous) return {action:"insert",change:"first_seen"};
  if (previous.content_hash === current.content_hash) return {action:"touch",change:"unchanged"};
  return {action:"update",change:"attributes_or_geometry_changed"};
}
export function deduplicatePageFeatures(features) {
  const byId = new Map();
  let duplicates = 0;
  for (const feature of features ?? []) {
    const id = getStableSourceId(feature);
    if (!id) continue;
    if (byId.has(id)) { duplicates++; continue; }
    byId.set(id, feature);
  }
  return {features:[...byId.values()],duplicateCount:duplicates,missingIdCount:(features ?? []).filter(feature => !getStableSourceId(feature)).length};
}
