import test from "node:test";
import assert from "node:assert/strict";
import { featureTouchesRadius, clipPolygonCollectionToRadius } from "../docs/map-radius-filter.mjs";

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

test("GeometryCollection applies radius checks to its child geometries", () => {
  const collection = {
    type: "Feature",
    properties: {},
    geometry: { type: "GeometryCollection", geometries: [
      { type: "Point", coordinates: [center.lon, center.lat] },
      { type: "Point", coordinates: [center.lon + 0.5, center.lat + 0.5] }
    ] }
  };
  assert.equal(featureTouchesRadius(collection, center, radius), true);
  const outside = {
    ...collection,
    geometry: { type: "GeometryCollection", geometries: [
      { type: "Point", coordinates: [center.lon + 0.5, center.lat + 0.5] },
      { type: "LineString", coordinates: [
        [center.lon + 0.5, center.lat + 0.5],
        [center.lon + 0.6, center.lat + 0.6]
      ] }
    ] }
  };
  assert.equal(featureTouchesRadius(outside, center, radius), false);
});

test("polygon clipping passes polygon and circle to intersection and keeps clipped properties", () => {
  const polygon = { type: "Feature", properties: { id: 7 }, geometry: { type: "Polygon", coordinates: [] } };
  const clipped = { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[0,0],[1,0],[1,1],[0,0]]] } };
  let circleArgs, intersectionArgs;
  const turf = {
    circle: (...args) => (circleArgs = args, { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [] } }),
    featureCollection: features => ({ type: "FeatureCollection", features }),
    intersect: fc => (intersectionArgs = fc.features, clipped)
  };
  const result = clipPolygonCollectionToRadius({ type: "FeatureCollection", features: [polygon] }, center, radius, turf);
  assert.deepEqual(circleArgs[0], [center.lon, center.lat]);
  assert.equal(circleArgs[1], radius / 1000);
  assert.equal(intersectionArgs.length, 2);
  assert.equal(result.features.length, 1);
  assert.deepEqual(result.features[0].properties, { id: 7 });
});

test("polygon clipping drops polygons with no intersection", () => {
  const polygon = { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [] } };
  const turf = {
    circle: () => ({ type: "Feature", geometry: { type: "Polygon", coordinates: [] } }),
    featureCollection: features => ({ features }),
    intersect: () => null
  };
  const result = clipPolygonCollectionToRadius({ type: "FeatureCollection", features: [polygon] }, center, radius, turf);
  assert.equal(result.features.length, 0);
});
