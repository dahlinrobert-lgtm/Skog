import test from "node:test";
import assert from "node:assert/strict";
import { arcgisGeometryToGeoJSON, compareValues, getComparisonPeriods } from "../docs/bevakning-core.mjs";

test("year-to-date compares the same calendar span in the previous year", () => {
  const now = new Date(2026, 9, 31, 14, 0, 0);
  const periods = getComparisonPeriods(2026, "all", now);
  assert.equal(periods.currentStart.getTime(), new Date(2026, 0, 1).getTime());
  assert.equal(periods.currentEnd.getTime(), new Date(2026, 10, 1).getTime());
  assert.equal(periods.previousStart.getTime(), new Date(2025, 0, 1).getTime());
  assert.equal(periods.previousEnd.getTime(), new Date(2025, 10, 1).getTime());
});

test("selected month compares with the immediately preceding month", () => {
  const october = getComparisonPeriods(2026, "10");
  assert.equal(october.currentStart.getTime(), new Date(2026, 9, 1).getTime());
  assert.equal(october.currentEnd.getTime(), new Date(2026, 10, 1).getTime());
  assert.equal(october.previousStart.getTime(), new Date(2026, 8, 1).getTime());
  assert.equal(october.previousEnd.getTime(), new Date(2026, 9, 1).getTime());
});

test("January compares with December of the previous year", () => {
  const january = getComparisonPeriods(2026, "01");
  assert.equal(january.previousStart.getTime(), new Date(2025, 11, 1).getTime());
  assert.equal(january.previousEnd.getTime(), new Date(2026, 0, 1).getTime());
});

test("comparison metrics handle zero baselines and percentage change", () => {
  assert.deepEqual(compareValues(15, 10), { difference: 5, percent: 50 });
  assert.deepEqual(compareValues(0, 0), { difference: 0, percent: null });
  assert.deepEqual(compareValues(4, 0), { difference: 4, percent: null });
});

test("ArcGIS rings are converted to a polygon with an interior hole", () => {
  const outer = [[0,0],[0,10],[10,10],[10,0],[0,0]];
  const hole = [[2,2],[8,2],[8,8],[2,8],[2,2]];
  const result = arcgisGeometryToGeoJSON({ rings: [outer, hole], spatialReference: { wkid: 4326 } });
  assert.equal(result.type, "Polygon");
  assert.equal(result.coordinates.length, 2);
});

test("disjoint ArcGIS exterior rings are converted to a multipolygon", () => {
  const a = [[0,0],[0,2],[2,2],[2,0],[0,0]];
  const b = [[4,4],[4,6],[6,6],[6,4],[4,4]];
  const result = arcgisGeometryToGeoJSON({ rings: [a, b] });
  assert.equal(result.type, "MultiPolygon");
  assert.equal(result.coordinates.length, 2);
});

test("ArcGIS points and paths are retained", () => {
  assert.deepEqual(arcgisGeometryToGeoJSON({ x: 19.5, y: 63.5 }), { type: "Point", coordinates: [19.5, 63.5] });
  assert.deepEqual(arcgisGeometryToGeoJSON({ paths: [[[0,0],[1,1]]] }), { type: "LineString", coordinates: [[0,0],[1,1]] });
});
