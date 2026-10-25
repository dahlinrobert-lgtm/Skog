import { filterFeatureCollectionToRadius } from "../docs/map-radius-filter.mjs";

const center = { lat: 63.74646, lon: 19.66455 };
const radii = [2_000, 10_000, 50_000];
const featureCount = Number(process.env.FEATURE_COUNT || 5_000);
if (!Number.isInteger(featureCount) || featureCount < 1) throw new TypeError("FEATURE_COUNT must be a positive integer");

const features = Array.from({ length: featureCount }, (_, i) => {
  // Deterministic spread: nearby, mid-range and distant points are all represented.
  const lat = center.lat + (((i * 37) % 2_000) - 1_000) / 10_000;
  const lon = center.lon + (((i * 71) % 2_000) - 1_000) / 10_000;
  return {
    type: "Feature",
    id: i + 1,
    properties: {},
    geometry: { type: "Point", coordinates: [lon, lat] }
  };
});
const collection = { type: "FeatureCollection", features };

console.log(JSON.stringify({
  benchmark: "map-radius-filter",
  dataset: "deterministic synthetic point features; not a live ArcGIS response",
  featureCount,
  results: radii.map(radiusMeters => {
    const result = filterFeatureCollectionToRadius(collection, center, radiusMeters);
    return {
      radiusMeters,
      inputFeatures: result.filterStats.inputFeatures,
      outputFeatures: result.filterStats.outputFeatures,
      filteredOutside: result.filterStats.filteredOutside,
      durationMs: result.filterStats.durationMs
    };
  })
}, null, 2));
