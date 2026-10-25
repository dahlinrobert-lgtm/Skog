import test from "node:test";
import assert from "node:assert/strict";
import { createLocalMatchPreview, toDatabaseArea } from "../src/watch-area-preview.mjs";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); }
  };
}

test("local preview matches radius and polygon areas against local observations", () => {
  const storage = memoryStorage({
    "skogskoll.watchAreas.v1": JSON.stringify([
      { id: "r1", name: "Nära skiftet", type: "radius", center: [19.66455, 63.74646], radiusM: 5000 },
      { id: "p1", name: "Polygonen", type: "polygon", geometry: { type: "Polygon", coordinates: [[[19.6,63.7],[19.7,63.7],[19.7,63.8],[19.6,63.8],[19.6,63.7]]] } }
    ]),
    "skogskoll.watchMatches.v1": JSON.stringify([
      { sourceId: "near", label: "Nära", geometry: { type: "Point", coordinates: [19.67,63.75] } },
      { sourceId: "far", label: "Långt bort", geometry: { type: "Point", coordinates: [20.1,64.1] } }
    ]),
    "skogskoll.alertPreferences.v1": JSON.stringify({ matchPref: true })
  });
  const preview = createLocalMatchPreview({ storage });
  const results = preview.run();
  assert.equal(results.length, 2);
  assert.deepEqual(new Set(results.map(item => item.observationId)), new Set(["near"]));
  assert.ok(results.every(item => item.match));
});

test("preview can list nonmatching pairs only when match requirement is switched off", () => {
  const storage = memoryStorage({
    "skogskoll.watchAreas.v1": JSON.stringify([{ id: "r1", name: "Circle", type: "radius", center: [0,0], radiusM: 1000 }]),
    "skogskoll.watchMatches.v1": JSON.stringify([{ sourceId: "far", geometry: { type: "Point", coordinates: [1,1] } }]),
    "skogskoll.alertPreferences.v1": JSON.stringify({ matchPref: false })
  });
  const results = createLocalMatchPreview({ storage }).run();
  assert.equal(results.length, 1);
  assert.equal(results[0].match, false);
});

test("database adapter maps radius to Point plus radius_m and polygons to geometry with null radius", () => {
  const radius = toDatabaseArea({ name: "A", type: "radius", center: [19.6,63.7], radiusM: 2500 }, "user-1");
  assert.deepEqual(radius.geom, { type: "Point", coordinates: [19.6,63.7] });
  assert.equal(radius.radius_m, 2500);
  const geometry = { type: "Polygon", coordinates: [[[0,0],[1,0],[1,1],[0,0]]] };
  const polygon = toDatabaseArea({ name: "B", type: "polygon", geometry }, "user-2");
  assert.deepEqual(polygon.geom, geometry);
  assert.equal(polygon.radius_m, null);
});

test("database adapter rejects invalid radius or unsupported geometry", () => {
  assert.throws(() => toDatabaseArea({ name: "A", type: "radius", center: [0,0], radiusM: 5 }, "u"), /between 100 and 100000/);
  assert.throws(() => toDatabaseArea({ name: "B", type: "polygon", geometry: { type: "Point", coordinates: [0,0] } }, "u"), /Polygon or MultiPolygon/);
});
