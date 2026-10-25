import { geometryMatchesWatchArea } from "./geometry-match.mjs";

const DEFAULT_TABLE = "skogskoll.watchMatches.v1";
const DEFAULT_PREFS = "skogskoll.alertPreferences.v1";

function safeRead(storage, key, fallback) {
  try {
    const value = storage.getItem(key);
    return value == null ? fallback : JSON.parse(value);
  } catch {
    return fallback;
  }
}

function toDatabaseArea(area, userId) {
  if (!area || typeof area.name !== "string" || !area.name.trim()) {
    throw new TypeError("Watch area must have a name.");
  }
  if (area.type === "radius") {
    const [lon, lat] = area.center ?? [];
    const radiusM = Number(area.radiusM);
    if (!Number.isFinite(lon) || !Number.isFinite(lat) || lon < -180 || lon > 180 || lat < -90 || lat > 90) {
      throw new TypeError("Radius center must be valid WGS84 [longitude, latitude].");
    }
    if (!Number.isInteger(radiusM) || radiusM < 100 || radiusM > 100000) {
      throw new TypeError("Radius must be between 100 and 100000 metres.");
    }
    return {
      user_id: userId,
      name: area.name.trim(),
      geom: { type: "Point", coordinates: [lon, lat] },
      radius_m: radiusM,
      enabled: area.enabled !== false
    };
  }
  if (area.type === "polygon") {
    const geometry = area.geometry;
    if (!geometry || !["Polygon", "MultiPolygon"].includes(geometry.type)) {
      throw new TypeError("Polygon area must contain a GeoJSON Polygon or MultiPolygon.");
    }
    return {
      user_id: userId,
      name: area.name.trim(),
      geom: geometry,
      radius_m: null,
      enabled: area.enabled !== false
    };
  }
  throw new TypeError("Unsupported watch-area type.");
}

function matchesLocally(observation, area) {
  return geometryMatchesWatchArea(observation?.geometry, area);
}

/**
 * Testable, opt-in browser preview.
 * The preview only reads local mock observations and local watch areas; it never
 * calls Supabase and never generates/delivers alerts.
 */
export function createLocalMatchPreview({
  storage = globalThis.localStorage,
  areaKey = "skogskoll.watchAreas.v1",
  observationKey = DEFAULT_TABLE,
  prefsKey = DEFAULT_PREFS
} = {}) {
  return {
    listAreas() {
      const areas = safeRead(storage, areaKey, []);
      return Array.isArray(areas) ? areas : [];
    },
    listObservations() {
      const observations = safeRead(storage, observationKey, []);
      return Array.isArray(observations) ? observations : [];
    },
    run() {
      const areas = this.listAreas();
      const observations = this.listObservations();
      const preferences = safeRead(storage, prefsKey, {});
      const requireMatch = preferences.matchPref !== false;
      const results = [];
      for (const area of areas) {
        for (const observation of observations) {
          const matched = matchesLocally(observation, area);
          if (requireMatch && !matched) continue;
          results.push({
            areaId: area.id,
            areaName: area.name,
            observationId: observation.sourceId ?? observation.id ?? null,
            observationLabel: observation.label ?? observation.attributes?.Beteckn ?? observation.attributes?.OBJECTID ?? "Testobservation",
            match: matched,
            eventType: observation.eventType ?? "test"
          });
        }
      }
      return results;
    },
    saveObservations(observations) {
      if (!Array.isArray(observations)) throw new TypeError("Observations must be an array.");
      storage.setItem(observationKey, JSON.stringify(observations));
    },
    toDatabaseArea(area, userId) {
      return toDatabaseArea(area, userId);
    }
  };
}

export { toDatabaseArea };
