import test from "node:test";
import assert from "node:assert/strict";
import { geometryMatchesWatchArea } from "../src/geometry-match.mjs";

const radius = { type: "radius", center: [19.66455, 63.74646], radiusM: 1000 };
const square = { type: "Polygon", coordinates: [[[19.65,63.73],[19.68,63.73],[19.68,63.76],[19.65,63.76],[19.65,63.73]]] };

test("radius matches points inside and rejects points outside", () => {
  assert.equal(geometryMatchesWatchArea({type:"Point",coordinates:[19.665,63.747]},radius),true);
  assert.equal(geometryMatchesWatchArea({type:"Point",coordinates:[20,64]},radius),false);
});
test("radius matches a line crossing the circle even when endpoints are outside", () => {
  assert.equal(geometryMatchesWatchArea({type:"LineString",coordinates:[[19.5,63.746],[19.8,63.746]]},radius),true);
});
test("radius matches a polygon containing the watch center", () => {
  assert.equal(geometryMatchesWatchArea({type:"Polygon",coordinates:[[[19.6,63.7],[19.8,63.7],[19.8,63.8],[19.6,63.8],[19.6,63.7]]]},radius),true);
});
test("polygon watch area matches contained points and crossing lines", () => {
  const watch={type:"polygon",geometry:square};
  assert.equal(geometryMatchesWatchArea({type:"Point",coordinates:[19.66,63.745]},watch),true);
  assert.equal(geometryMatchesWatchArea({type:"Point",coordinates:[20,64]},watch),false);
  assert.equal(geometryMatchesWatchArea({type:"LineString",coordinates:[[19.6,63.745],[19.7,63.745]]},watch),true);
});
test("polygon watch area matches overlapping polygons and rejects disjoint ones", () => {
  const watch={type:"polygon",geometry:square};
  assert.equal(geometryMatchesWatchArea({type:"Polygon",coordinates:[[[19.67,63.74],[19.69,63.74],[19.69,63.75],[19.67,63.75],[19.67,63.74]]]},watch),true);
  assert.equal(geometryMatchesWatchArea({type:"Polygon",coordinates:[[[20,64],[20.1,64],[20.1,64.1],[20,64.1],[20,64]]]},watch),false);
});
test("invalid geometry and watch areas fail closed", () => {
  assert.equal(geometryMatchesWatchArea(null,radius),false);
  assert.equal(geometryMatchesWatchArea({type:"Point",coordinates:[19.66,63.74]},{type:"radius",center:[0,0],radiusM:-1}),false);
  assert.equal(geometryMatchesWatchArea({type:"Point",coordinates:[19.66,63.74]},{type:"polygon",geometry:{type:"Point",coordinates:[0,0]}}),false);
});
