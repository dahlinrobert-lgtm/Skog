const EARTH_RADIUS_M = 6371008.8;

function validPosition(position) {
  return Array.isArray(position) && position.length >= 2 &&
    Number.isFinite(position[0]) && Number.isFinite(position[1]) &&
    position[0] >= -180 && position[0] <= 180 &&
    position[1] >= -90 && position[1] <= 90;
}

function positionsFromGeometry(geometry, out = []) {
  if (!geometry || typeof geometry !== "object") return out;
  const walk = value => {
    if (validPosition(value)) out.push(value);
    else if (Array.isArray(value)) value.forEach(walk);
  };
  walk(geometry.coordinates);
  return out;
}

function haversine(a, b) {
  const rad = value => value * Math.PI / 180;
  const dLat = rad(b[1] - a[1]);
  const dLon = rad(b[0] - a[0]);
  const lat1 = rad(a[1]);
  const lat2 = rad(b[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

function pointInRing(point, ring) {
  if (!Array.isArray(ring) || ring.length < 4) return false;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i], b = ring[j];
    if (!validPosition(a) || !validPosition(b)) continue;
    const crosses = ((a[1] > point[1]) !== (b[1] > point[1])) &&
      point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / ((b[1] - a[1]) || Number.EPSILON) + a[0];
    if (crosses) inside = !inside;
  }
  return inside;
}

function pointInPolygon(point, polygonCoordinates) {
  if (!Array.isArray(polygonCoordinates) || !polygonCoordinates.length) return false;
  if (!pointInRing(point, polygonCoordinates[0])) return false;
  return !polygonCoordinates.slice(1).some(ring => pointInRing(point, ring));
}

function segmentsIntersect(a, b, c, d) {
  const cross = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
  const onSegment = (p, q, r) =>
    q[0] >= Math.min(p[0], r[0]) - 1e-10 && q[0] <= Math.max(p[0], r[0]) + 1e-10 &&
    q[1] >= Math.min(p[1], r[1]) - 1e-10 && q[1] <= Math.max(p[1], r[1]) + 1e-10;
  const o1 = cross(a, b, c), o2 = cross(a, b, d), o3 = cross(c, d, a), o4 = cross(c, d, b);
  if (((o1 > 0 && o2 < 0) || (o1 < 0 && o2 > 0)) &&
      ((o3 > 0 && o4 < 0) || (o3 < 0 && o4 > 0))) return true;
  return (Math.abs(o1) < 1e-10 && onSegment(a, c, b)) ||
    (Math.abs(o2) < 1e-10 && onSegment(a, d, b)) ||
    (Math.abs(o3) < 1e-10 && onSegment(c, a, d)) ||
    (Math.abs(o4) < 1e-10 && onSegment(c, b, d));
}

function polygonRings(geometry) {
  if (geometry?.type === "Polygon") return geometry.coordinates ?? [];
  if (geometry?.type === "MultiPolygon") return (geometry.coordinates ?? []).flat();
  return [];
}

function polygonEdges(rings) {
  return rings.flatMap(ring => {
    if (!Array.isArray(ring) || ring.length < 2) return [];
    return ring.slice(1).map((point, i) => [ring[i], point]).filter(edge => validPosition(edge[0]) && validPosition(edge[1]));
  });
}

function geometryIntersectsPolygon(geometry, polygon) {
  const rings = polygonRings(polygon);
  if (!rings.length) return false;
  const sourcePositions = positionsFromGeometry(geometry);
  if (sourcePositions.some(position => rings.some(ring => pointInRing(position, ring)))) return true;
  const sourceRings = polygonRings(geometry);
  if (sourceRings.some(ring => ring.some(position => pointInPolygon(position, rings)))) return true;
  const targetEdges = polygonEdges(rings);
  const sourceEdges = [
    ...polygonEdges(sourceRings),
    ...((geometry?.type === "LineString") ? polygonEdges([geometry.coordinates ?? []]) : []),
    ...((geometry?.type === "MultiLineString") ? (geometry.coordinates ?? []).flatMap(line => polygonEdges([line])) : [])
  ];
  return sourceEdges.some(([a, b]) => targetEdges.some(([c, d]) => segmentsIntersect(a, b, c, d)));
}

/**
 * Matches GeoJSON feature geometry to a watch area.
 * watchArea is {type:"radius", center:[lon,lat], radiusM} or
 * {type:"polygon", geometry:{type:"Polygon"|"MultiPolygon", coordinates:[...]}}.
 * Uses a conservative vertex/containment/edge-intersection approximation; no ownership inference.
 */
export function geometryMatchesWatchArea(featureGeometry, watchArea) {
  if (!featureGeometry || !watchArea) return false;
  if (watchArea.type === "polygon") {
    const polygon = watchArea.geometry;
    if (!["Polygon", "MultiPolygon"].includes(polygon?.type)) return false;
    return geometryIntersectsPolygon(featureGeometry, polygon);
  }
  if (watchArea.type !== "radius" || !validPosition(watchArea.center) ||
      !Number.isFinite(watchArea.radiusM) || watchArea.radiusM < 0) return false;
  const positions = positionsFromGeometry(featureGeometry);
  if (!positions.length) return false;
  if (positions.some(position => haversine(position, watchArea.center) <= watchArea.radiusM)) return true;
  const rings = polygonRings(featureGeometry);
  if (rings.some(ring => pointInRing(watchArea.center, ring))) return true;
  // Segment sampling prevents missing a long line crossing the circle when its endpoints are outside.
  const lines = [];
  if (featureGeometry.type === "LineString") lines.push(featureGeometry.coordinates ?? []);
  if (featureGeometry.type === "MultiLineString") lines.push(...(featureGeometry.coordinates ?? []));
  for (const ring of rings) lines.push(ring);
  for (const line of lines) {
    for (let i = 1; i < line.length; i++) {
      const a = line[i - 1], b = line[i];
      if (!validPosition(a) || !validPosition(b)) continue;
      const length = haversine(a, b);
      const steps = Math.min(1000, Math.max(1, Math.ceil(length / Math.max(25, watchArea.radiusM / 2 || 25))));
      for (let step = 1; step < steps; step++) {
        const t = step / steps;
        const point = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
        if (haversine(point, watchArea.center) <= watchArea.radiusM) return true;
      }
    }
  }
  return false;
}
