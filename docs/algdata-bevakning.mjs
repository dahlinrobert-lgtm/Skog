const DATA_URL = "https://raw.githubusercontent.com/dahlinrobert-lgtm/alg-grasmyr/main/data/regional_pilot_dashboard.json";

const numberFormat = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1 });
const dateFormat = new Intl.DateTimeFormat("sv-SE", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
const dateLabel = value => {
  if (!value) return "Ej observerat";
  const date = new Date(value + "T12:00:00Z");
  return Number.isNaN(date.getTime()) ? "Ej observerat" : dateFormat.format(date);
};
const safe = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));
const formatCount = value => value === null || value === undefined ? "–" : numberFormat.format(value);

function renderFailure(message) {
  const status = document.getElementById("elkdataStatus");
  if (status) status.textContent = message;
  const body = document.getElementById("elkdataRows");
  if (body) body.innerHTML = '<tr><td colspan="8" class="elkdata-empty">Älgdata kunde inte läsas just nu. Avverkningsbevakningen fungerar fortfarande som vanligt.</td></tr>';
}

function initDashboard(data) {
  const areas = Array.isArray(data.areas) ? data.areas : [];
  const latestDate = data.latest_snapshot_date || null;
  const latestAreas = areas.filter(area => area.latest_snapshot_date === latestDate);
  const observed = areas.filter(area => area.first_observed_positive_date);
  const increased = areas.filter(area => area.latest_observed_increase_date === latestDate);
  document.getElementById("elkdataAreaCount").textContent = numberFormat.format(areas.length);
  document.getElementById("elkdataCoverage").textContent = numberFormat.format(latestAreas.length) + " av " + numberFormat.format(areas.length);
  document.getElementById("elkdataFirstCount").textContent = numberFormat.format(observed.length);
  document.getElementById("elkdataIncreaseCount").textContent = numberFormat.format(increased.length);
  document.getElementById("elkdataSnapshotDate").textContent = dateLabel(latestDate);
  document.getElementById("elkdataStatus").textContent =
    "Senaste sammanställda uttag: " + dateLabel(latestDate) +
    ". " + numberFormat.format(latestAreas.length) + " av " + numberFormat.format(areas.length) +
    " områden har data för detta datum.";

  const counties = [...new Set(areas.map(area => area.county).filter(Boolean))].sort((a, b) => a.localeCompare(b, "sv"));
  const countySelect = document.getElementById("elkdataCounty");
  countySelect.innerHTML = '<option value="all">Alla län</option>' +
    counties.map(county => '<option value="' + safe(county) + '">' + safe(county) + '</option>').join("");

  const search = document.getElementById("elkdataSearch");
  function renderRows() {
    const county = countySelect.value;
    const query = search.value.trim().toLocaleLowerCase("sv");
    const filtered = areas.filter(area => {
      if (county !== "all" && area.county !== county) return false;
      const haystack = [area.area_name, area.area_display_id, area.county, area.afo].join(" ").toLocaleLowerCase("sv");
      return !query || haystack.includes(query);
    }).sort((a, b) =>
      String(b.latest_observed_increase_date || "").localeCompare(String(a.latest_observed_increase_date || "")) ||
      String(b.latest_snapshot_date || "").localeCompare(String(a.latest_snapshot_date || "")) ||
      String(a.area_name || "").localeCompare(String(b.area_name || ""), "sv")
    );

    document.getElementById("elkdataResultCount").textContent = numberFormat.format(filtered.length) + " områden";
    document.getElementById("elkdataRows").innerHTML = filtered.length ? filtered.map(area => {
      const latest = area.latest_total === null ? "–" : formatCount(area.latest_total);
      const delta = area.latest_delta;
      const deltaText = delta === null ? "–" : (delta > 0 ? "+" : "") + formatCount(delta);
      const deltaClass = delta > 0 ? "elkdata-positive" : "";
      return '<tr>' +
        '<td><strong>' + safe(area.area_name || "Namn saknas") + '</strong><small>' + safe(area.area_display_id || area.area_key) + '</small></td>' +
        '<td>' + safe(area.county || "–") + '</td>' +
        '<td>' + safe(area.afo || "–") + '</td>' +
        '<td class="elkdata-number">' + latest + '</td>' +
        '<td class="elkdata-number ' + deltaClass + '">' + deltaText + '</td>' +
        '<td>' + dateLabel(area.first_observed_positive_date) + '</td>' +
        '<td>' + dateLabel(area.latest_observed_increase_date) + '</td>' +
        '<td>' + dateLabel(area.latest_snapshot_date) + '</td>' +
      '</tr>';
    }).join("") : '<tr><td colspan="8" class="elkdata-empty">Inga områden matchar filtreringen.</td></tr>';
  }
  countySelect.addEventListener("change", renderRows);
  search.addEventListener("input", renderRows);
  renderRows();
}

async function loadElkdata() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    if (data.schema_version !== 1 || !Array.isArray(data.areas)) throw new Error("Okänt dataformat");
    initDashboard(data);
  } catch (error) {
    renderFailure("Älgdatadelen är tillfälligt otillgänglig (" + (error.message || "okänt fel") + ").");
  }
}

loadElkdata();
