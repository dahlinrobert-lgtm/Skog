const url = process.env.SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (typeof url !== "string" || !/^https:\/\//.test(url)) {
  throw new Error("SUPABASE_URL is missing or is not HTTPS");
}
if (typeof key !== "string" || key.trim() === "") {
  throw new Error("SUPABASE_SERVICE_ROLE_KEY is missing");
}

const base = url.replace(/\/$/, "");
const headers = {
  apikey: key,
  authorization: `Bearer ${key}`,
  accept: "application/json"
};

async function checkTable(table) {
  const query = new URLSearchParams({ select: "id", limit: "1" });
  const response = await fetch(`${base}/rest/v1/${table}?${query}`, {
    method: "GET",
    headers,
    signal: AbortSignal.timeout(15000)
  });
  if (!response.ok) {
    // Do not include response bodies: they may contain project-specific details.
    throw new Error(`Supabase REST read failed for ${table}: HTTP ${response.status}`);
  }
  const rows = await response.json();
  if (!Array.isArray(rows)) throw new Error(`Unexpected REST response for ${table}`);
  return { table, ok: true, sample_rows_returned: rows.length };
}

const results = [];
for (const table of ["scan_sessions", "poll_runs"]) {
  results.push(await checkTable(table));
}
console.log(JSON.stringify({
  checked_at: new Date().toISOString(),
  mode: "read-only; no RPC writes; no ingestion; no alerts",
  checks: results,
  conclusion: "service-role REST authentication and required worker SELECT permissions succeeded"
}, null, 2));
