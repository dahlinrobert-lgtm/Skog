import { mkdir, writeFile } from "node:fs/promises";
import { createArcGisSource } from "../src/supabase-adapters.mjs";

const output = "skogskoll/reports/worker-metadata-probe-latest.json";
const report = {
  checked_at: new Date().toISOString(),
  mode: "read-only; ArcGIS layer metadata only; no Supabase connection; no ingestion; no alerts",
  source: "skogsstyrelsen.harvest_notifications",
  ok: false
};

try {
  const source = createArcGisSource();
  const metadata = await source.getSnapshotMetadata();
  const required = [
    "product", "endpoint", "layer", "query_definition", "coverage_key",
    "schema_version", "identity_version", "customer_visibility"
  ];
  const missing = required.filter(key =>
    typeof metadata[key] !== "string" || metadata[key].trim() === ""
  );
  if (missing.length) throw new Error("Live adapter metadata is incomplete: " + missing.join(", "));
  if (metadata.customer_visibility !== "not_assessed" || metadata.rights_evidence_ref !== null) {
    throw new Error("Unexpected rights/customer-visibility metadata; fail closed");
  }
  report.ok = true;
  report.metadata = metadata;
  report.summary = "Live getSnapshotMetadata() succeeded against the configured ArcGIS layer.";
} catch (error) {
  report.error = String(error?.stack ?? error);
  report.summary = "Live worker metadata probe failed; ingestion remains disabled.";
  process.exitCode = 1;
}

await mkdir("skogskoll/reports", { recursive: true });
await writeFile(output, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
