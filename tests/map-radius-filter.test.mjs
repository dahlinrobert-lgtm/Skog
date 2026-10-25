import test from "node:test";
import assert from "node:assert/strict";
import { featureTouchesRadius } from "../src/map-radius-filter.mjs";

const center = { lat: 63.74646, lon: 19.66455 };
const radius = 10_000;
const point = (lat, lon) => ({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, lat] } });

test("point is included inside radius and excluded outside", () => {
  assert.equal(featureTouchesRadius(point(center.lat, center.lon), center, radius), true);
  assert.equal(featureTouchesRadius(point(63.95, center.lon), center, radius), false);
});

test("line is included when crossing the circle even if endpoints are outside", () => {
  const line = { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [
    [center.lon - 0.2, center.lat], [center.lon + 0.2, center.lat]
  ] } };
  assert.equal(featureTouchesRadius(line, center, radius), true);
});

test("polygon is included when it contains circle center and excluded when far away", () => {
  const inside = { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[
    [center.lon - 0.01, center.lat - 0.01], [center.lon + 0.01, center.lat - 0.01],
    [center.lon + 0.01, center.lat + 0.01], [center.lon - 0.01, center.lat + 0.01],
    [center.lon - 0.01, center.lat - 0.01]
  ]] } };
  const outside = { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[
    [center.lon + 0.5, center.lat + 0.5], [center.lon + 0.51, center.lat + 0.5],
    [center.lon + 0.51, center.lat + 0.51], [center.lon + 0.5, center.lat + 0.51],
    [center.lon + 0.5, center.lat + 0.5]
  ]] } };
  assert.equal(featureTouchesRadius(inside, center, radius), true);
  assert.equal(featureTouchesRadius(outside, center, radius), false);
});
