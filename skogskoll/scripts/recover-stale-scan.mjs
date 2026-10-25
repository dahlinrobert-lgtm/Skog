import { SOURCE_ID } from "../src/observation-core.mjs";
import { createSupabaseStore } from "../src/supabase-adapters.mjs";

function positiveInteger(value, fallback, name, minimum = 1) {
  if (value == null || value === "") return fallback;
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < minimum) {
    throw new Error(`${name} must be an integer >= ${minimum}`);
  }
  return parsed;
}

async function main() {
  // Recovery is intentionally manual. It changes a running DB session to failed.
  if (process.env.SKOGSKOLL_ENABLE_STALE_RECOVERY !== "YES") {
    throw new Error("Stale-session recovery is disabled. Set SKOGSKOLL_ENABLE_STALE_RECOVERY=YES only after confirming no worker is running.");
  }

  const staleMinutes = positiveInteger(process.env.SKOGSKOLL_STALE_MINUTES, 1440, "SKOGSKOLL_STALE_MINUTES", 60);
  const staleBefore = new Date(Date.now() - staleMinutes * 60_000).toISOString();
  const store = createSupabaseStore({
    url: process.env.SUPABASE_URL,
    serviceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY
  });
  const result = await store.recoverStaleScan({
    sourceKey: SOURCE_ID,
    staleBefore,
    reason: `manual recovery: session older than ${staleMinutes} minutes`
  });

  console.log(JSON.stringify({
    source: SOURCE_ID,
    staleBefore,
    staleMinutes,
    recovered: Array.isArray(result) ? result.length : result ? 1 : 0,
    result,
    note: "Recovery only marks the stale session failed. It does not resume ingestion, delete observations, reconcile inactive records, or send alerts."
  }, null, 2));
}

main().catch(error => {
  console.error(`Skogskoll stale recovery stopped: ${String(error?.message ?? error)}`);
  process.exitCode = 1;
});
