import { runScanBatch } from "../src/scan-worker-core.mjs";
import { createProductionAdapters } from "../src/supabase-adapters.mjs";

function positiveInteger(value, fallback, name) {
  if (value == null || value === "") return fallback;
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 1) throw new Error(`${name} must be a positive integer`);
  return parsed;
}

async function main() {
  // Explicit opt-in prevents an accidental local invocation from writing data.
  if (process.env.SKOGSKOLL_ENABLE_INGESTION !== "YES") {
    throw new Error("Ingestion is disabled. Set SKOGSKOLL_ENABLE_INGESTION=YES to explicitly enable a bounded database-writing run.");
  }
  const mode = process.env.SKOGSKOLL_SCAN_MODE;
  if (mode !== "baseline" && mode !== "incremental") {
    throw new Error("Set SKOGSKOLL_SCAN_MODE explicitly to baseline or incremental.");
  }

  const pageSize = positiveInteger(process.env.SKOGSKOLL_PAGE_SIZE, 500, "SKOGSKOLL_PAGE_SIZE");
  const maxPages = positiveInteger(process.env.SKOGSKOLL_MAX_PAGES, 10, "SKOGSKOLL_MAX_PAGES");
  const { source, store } = createProductionAdapters(process.env, {
    source: { pageLimit: pageSize }
  });

  const result = await runScanBatch({ source, store, pageSize, maxPages, mode });
  console.log(JSON.stringify({
    ...result,
    source: source.key,
    mode,
    alertsEnabled: false,
    note: "This run does not send email or push notifications and does not reconcile unseen records as inactive."
  }, null, 2));
}

main().catch(error => {
  // Avoid printing environment or request headers, which may contain secrets.
  console.error(`Skogskoll ingestion stopped: ${String(error?.message ?? error)}`);
  process.exitCode = 1;
});
