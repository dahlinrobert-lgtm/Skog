// Skogskoll – manuell, engångsvis diagnostik av Min kartas fastighetsgeometri
// Kör endast i DevTools Console på https://minkarta.lantmateriet.se/ efter att du själv har valt fastighet.
// Ingen polling, inga loopade anrop, inga cookies/token skickas till annan domän.
// Detta använder en odokumenterad intern endpoint och är endast en tillfällig diagnostik – inte produktionsintegration.
(async () => {
  const objectId = prompt("Klistra in objektidentitet från fastigheten i Min karta:");
  if (!objectId) return;
  if (!/^[0-9a-f-]{20,}$/i.test(objectId.trim())) {
    console.error("Objektidentiteten ser inte giltig ut.");
    return;
  }
  const url = "/api/searchservice/fastighetsgeometri/v1?objektidentitet=" + encodeURIComponent(objectId.trim());
  try {
    const response = await fetch(url, { method: "GET", credentials: "same-origin", headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    const coordinatePairs = [];
    const visit = (value) => {
      if (!value) return;
      if (Array.isArray(value)) {
        if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
          coordinatePairs.push([value[0], value[1]]);
          return;
        }
        for (const item of value) visit(item);
      } else if (typeof value === "object") {
        for (const [key, item] of Object.entries(value)) {
          if (key.toLowerCase() === "coordinates" || typeof item === "object") visit(item);
        }
      }
    };
    visit(data);
    const xs = coordinatePairs.map(p => p[0]);
    const ys = coordinatePairs.map(p => p[1]);
    const bounds = coordinatePairs.length ? {
      minX: Math.min(...xs), minY: Math.min(...ys),
      maxX: Math.max(...xs), maxY: Math.max(...ys),
      coordinatePairCount: coordinatePairs.length
    } : null;
    console.group("Skogskoll · Min karta geometri-test");
    console.log("HTTP", response.status, "URL", url);
    console.log("Toppnivånycklar:", Object.keys(data || {}));
    console.log("Geometrityp:", data?.type || data?.geometry?.type || "se JSON");
    console.log("Koordinatintervall:", bounds);
    console.warn("Koordinatsystem är INTE fastställt av detta test. Koordinater som liknar meter får inte användas som lon/lat utan verifierad CRS-konvertering.");
    console.log("Rådata:", data);
    console.groupEnd();
    const blob = new Blob([JSON.stringify({
      diagnostic: "Skogskoll Min karta manual probe",
      fetchedAt: new Date().toISOString(),
      endpoint: url,
      httpStatus: response.status,
      topLevelKeys: Object.keys(data || {}),
      detectedBounds: bounds,
      crs: "UNVERIFIED — inspect official metadata before transforming",
      response: data
    }, null, 2)], { type: "application/json" });
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = "skogskoll-min-karta-geometry-probe.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
    alert("Test klart. JSON har laddats ned. Koordinatsystemet är inte verifierat; använd inte geometrin som WGS84 ännu.");
  } catch (error) {
    console.error("Min karta-anropet misslyckades:", error);
    alert("Anropet misslyckades: " + error.message + ". Kontrollera att du är på minkarta.lantmateriet.se och att fastigheten går att välja där.");
  }
})();
