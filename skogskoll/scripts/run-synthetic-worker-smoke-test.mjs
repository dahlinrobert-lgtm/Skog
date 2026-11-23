import { createSupabaseStore } from "../src/supabase-adapters.mjs";
import { runScanBatch } from "../src/scan-worker-core.mjs";
import { SOURCE_ID } from "../src/observation-core.mjs";

const ENABLE_FLAG = "SKOGSKOLL_ENABLE_SYNTHETIC_SMOKE_TEST";
const SYNTHETIC_SOURCE = "skogskoll:synthetic:worker-smoke-test";
const PAGE_SIZE = 2;
const FIXTURE_VARIANT = process.env.SKOGSKOLL_SYNTHETIC_FIXTURE_VARIANT ?? "unchanged";
if (!["unchanged", "change_feature_001"].includes(FIXTURE_VARIANT)) {
  throw new Error("Unsupported synthetic fixture variant");
}

if (process.env[ENABLE_FLAG] !== "YES") {
  throw new Error(`Synthetic worker smoke test is disabled. Set ${ENABLE_FLAG}=YES only for the dedicated test workflow.`);
}
if (SYNTHETIC_SOURCE === SOURCE_ID || !SYNTHETIC_SOURCE.startsWith("skogskoll:synthetic:")) {
  throw new Error("Synthetic source identity guard failed");
}

const url = process.env.SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !serviceRoleKey) throw new Error("Supabase test credentials are missing");
const apiHost = new URL(url).hostname;
if (apiHost !== "jdfekakdxmltaccslrkp.supabase.co") {
  throw new Error("Synthetic worker smoke test is restricted to the verified skogskoll-test Supabase project");
}

const store = createSupabaseStore({ url, serviceRoleKey });
const features = [
  {
    type: "Feature",
    id: "worker-smoke-feature-001",
    properties: {
      smoke_test: true,
      fixture: "skogskoll-worker-smoke-v1",
      sequence: FIXTURE_VARIANT === "change_feature_001" ? 101 : 1
    },
    geometry: null
  },
  { type: "Feature", id: "worker-smoke-feature-002", properties: { smoke_test: true, fixture: "skogskoll-worker-smoke-v1", sequence: 2 }, geometry: null }
];

const source = {
  key: SYNTHETIC_SOURCE,
  async getSnapshotMetadata() {
    return {
      product: "synthetic_worker_smoke",
      endpoint: "https://synthetic.invalid/skogskoll/worker-smoke/FeatureServer/0",
      layer: "0",
      query_definition: `fixture=skogskoll-worker-smoke-v1;variant=${FIXTURE_VARIANT};returnGeometry=true`,
      coverage_key: "synthetic-fixture-only-v1",
      schema_version: "synthetic-worker-smoke-schema-v1",
      identity_version: "stable-fixture-id-v1",
      customer_visibility: "not_assessed",
      rights_evidence_ref: null
    };
  },
  async getCount() { return features.length; },
  async getPage(offset, requestedSize) {
    return { features: features.slice(offset, offset + Math.min(requestedSize, PAGE_SIZE)), exceededTransferLimit: false };
  }
};

const result = await runScanBatch({ source, store, pageSize: PAGE_SIZE, maxPages: 1, mode: "baseline" });
if (result.status !== "complete" || result.fetchedCount !== features.length) {
  throw new Error("Synthetic worker smoke test did not complete the expected fixture");
}

console.log(JSON.stringify({
  result, source: SYNTHETIC_SOURCE, fixture: "skogskoll-worker-smoke-v1",
  fixtureVariant: FIXTURE_VARIANT, expectedChangedSourceIds: FIXTURE_VARIANT === "change_feature_001" ? ["worker-smoke-feature-001"] : [],
  pagesExpected: 1,
  alertsEnabled: false, productionSourceUsed: false,
  note: "Synthetic observations, poll runs, scan sessions and immutable snapshot envelopes are retained in the test project for audit; no cleanup deletes history."
}, null, 2));