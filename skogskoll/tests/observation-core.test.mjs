import test from "node:test";
import assert from "node:assert/strict";
import { classifyObservation, contentHash, deduplicatePageFeatures, getStableSourceId, normalizeFeature } from "../src/observation-core.mjs";
const a={type:"Feature",id:42,properties:{OBJECTID:42,Beteckn:"A-1",Inkomdatum:1761000000000},geometry:{type:"Point",coordinates:[19.6,63.7]}};

test("stable ID supports feature id and ArcGIS ObjectId fallbacks",()=>{assert.equal(getStableSourceId(a),"42");assert.equal(getStableSourceId({properties:{ObjectId:7}}),"7");assert.equal(getStableSourceId({properties:{}}),null);});
test("content hash ignores object key order but changes with content",()=>{assert.equal(contentHash({properties:{b:2,a:1}}),contentHash({properties:{a:1,b:2}}));assert.notEqual(contentHash(a),contentHash({...a,properties:{...a.properties,Beteckn:"A-2"}}));});
test("normalization rejects records without stable ID",()=>{assert.equal(normalizeFeature({properties:{}}).reason,"missing_stable_source_id");});
test("same source record is deduplicated across pages",()=>{const result=deduplicatePageFeatures([a,a,{properties:{}}]);assert.equal(result.features.length,1);assert.equal(result.duplicateCount,1);assert.equal(result.missingIdCount,1);});
test("classification distinguishes first-seen, unchanged and changed records",()=>{const current=normalizeFeature(a,"2026-10-25T00:00:00Z");assert.equal(classifyObservation(current,null).action,"insert");assert.equal(classifyObservation(current,{content_hash:current.content_hash}).action,"touch");assert.equal(classifyObservation(normalizeFeature({...a,properties:{...a.properties,Beteckn:"changed"}}),{content_hash:current.content_hash}).action,"update");});
test("source received date is separate from our observation time",()=>{
  const normalized=normalizeFeature(a,"2026-10-25T08:00:00.000Z");
  assert.equal(normalized.observed_at,"2026-10-25T08:00:00.000Z");
  assert.equal(normalized.source_received_at,1761000000000);
  assert.equal(normalized.source_created_at,1761000000000);
  assert.notEqual(normalized.observed_at,normalized.source_received_at);
});
