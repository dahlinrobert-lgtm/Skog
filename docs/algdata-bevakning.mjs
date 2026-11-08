const DATA_URL = "https://raw.githubusercontent.com/dahlinrobert-lgtm/alg-grasmyr/main/data/regional_pilot_dashboard.json";

async function loadElkdata() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    if (data.schema_version !== 1 || !Array.isArray(data.areas)) throw new Error("Okänt dataformat");
    window.dispatchEvent(new CustomEvent("skog:elkdata-loaded", { detail: data }));
  } catch (error) {
    window.dispatchEvent(new CustomEvent("skog:elkdata-error", {
      detail: { message: error.message || "Okänt fel" }
    }));
  }
}

window.addEventListener("skog:elkdata-refresh", loadElkdata);
loadElkdata();
