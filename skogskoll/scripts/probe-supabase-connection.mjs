const rawUrl = process.env.SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

function safeHost(value) {
  try { return new URL(value).hostname; } catch { return "invalid"; }
}

if (typeof rawUrl !== "string" || rawUrl.trim() === "") {
  throw new Error("SUPABASE_URL secret is missing");
}
if (typeof key !== "string" || key.trim() === "") {
  throw new Error("SUPABASE_SERVICE_ROLE_KEY secret is missing");
}

let parsedUrl;
try {
  parsedUrl = new URL(rawUrl.trim());
} catch {
  throw new Error("SUPABASE_URL is not a valid absolute URL");
}
if (parsedUrl.protocol !== "https:") {
  throw new Error("SUPABASE_URL must use HTTPS");
}
if (parsedUrl.username || parsedUrl.password || parsedUrl.search || parsedUrl.hash) {
  throw new Error("SUPABASE_URL must not contain credentials, query parameters or a fragment");
}
if (parsedUrl.pathname !== "/" && parsedUrl.pathname !== "") {
  throw new Error("SUPABASE_URL must be the project API origin only, without /dashboard or other path segments");
}
if (!parsedUrl.hostname.endsWith(".supabase.co")) {
  throw new Error("SUPABASE_URL host is not a standard Supabase project API hostname; received host: " + parsedUrl.hostname);
}

const base = parsedUrl.origin;
const headers = {
  apikey: key,
  authorization: `Bearer ${key}`,
  accept: "application/json"
};

async function checkTable(table) {
  const query = new URLSearchParams({ select: "id", limit: "1" });
  let response;
  try {
    response = await fetch(`${base}/rest/v1/${table}?${query}`, {
      method: "GET",
      headers,
      signal: AbortSignal.timeout(15000)
    });
  } catch (error) {
    throw new Error(`Supabase network request failed for ${table}: ${error?.name ?? "network error"}`);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok) {
    throw new Error(`Supabase REST read failed for ${table}: HTTP ${response.status}; content-type=${contentType || "missing"}; host=${safeHost(base)}`);
  }
  if (!contentType.toLowerCase().includes("application/json")) {
    throw new Error(`Expected JSON from Supabase REST for ${table}, received content-type=${contentType || "missing"}; host=${safeHost(base)}. Check that SUPABASE_URL is the project's API URL, not the Supabase Dashboard URL.`);
  }

  let rows;
  try {
    rows = await response.json();
  } catch {
    throw new Error(`Supabase REST returned invalid JSON for ${table}`);
  }
  if (!Array.isArray(rows)) throw new Error(`Unexpected Supabase REST response shape for ${table}`);
  return { table, ok: true, sample_rows_returned: rows.length };
}

const results = [];
for (const table of ["scan_sessions", "poll_runs"]) {
  results.push(await checkTable(table));
}
console.log(JSON.stringify({
  checked_at: new Date().toISOString(),
  mode: "read-only; no RPC writes; no ingestion; no alerts",
  api_host: parsedUrl.hostname,
  checks: results,
  conclusion: "service-role REST authentication and required worker SELECT permissions succeeded"
}, null, 2));
