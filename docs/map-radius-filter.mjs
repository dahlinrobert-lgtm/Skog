const EARTH_RADIUS_METERS = 6_371_008.8;

function distanceMeters(center, coord) {
  const toRad = n => n * Math.PI / 180;
  const lat1 = toRad(center.lat), lat2 = toRad(coord[1]);
  const dLat = lat2 - lat1, dLon = toRad(coord[0] - center.lon);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_METERS * Math.asin(Math.min(1, Math.sqrt(a)));
}

function pointToSegmentMeters(center, a, b) {
  // Local azimuthal approximation is sufficient over the supported <= 100 km radius.
  const lat0 = center.lat * Math.PI / 180;
  const xy = coord => [
    (coord[0] - center.lon) * 111_320 * Math.cos(lat0),
    (coord[1] - center.lat) * 110_540
  ];
  const p = [0, 0], A = xy(a), B = xy(b);
  const dx = B[0] - A[0], dy = B[1] - A[1];
  const den = dx * dx + dy * dy;
  const t = den ? Math.max(0, Math.min(1, ((p[0] - A[0]) * dx + (p[1] - A[1]) * dy) / den)) : 0;
  return Math.hypot(p[0] - (A[0] + t * dx), p[1] - (A[1] + t * dy));
}

function insideRing(point, ring) {
  let inside = false;
  const [x, y] = point;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    const intersects = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-15) + xi);
    if (intersects) inside = !inside;
  }
  return inside;
}

function pointInPolygon(point, polygon) {
  if (!polygon.length || !insideRing(point, polygon[0])) return false;
  for (let i = 1; i < polygon.length; i++) {
    if (insideRing(point, polygon[i])) return false; // point lies inside a hole
  }
  return true;
}

export function featureTouchesRadius(feature, center, radiusMeters, toleranceMeters = 2) {
  if (!center || !Number.isFinite(center.lat) || !Number.isFinite(center.lon) ||
      !Number.isFinite(radiusMeters) || radiusMeters < 0) {
    throw new TypeError("center coordinates and a non-negative radius are required");
  }
  const geometry = feature?.geometry;
  if (!geometry || typeof geometry.type !== "string") return false;

  const within = coord => Array.isArray(coord) && coord.length >= 2 &&
    Number.isFinite(coord[0]) && Number.isFinite(coord[1]) &&
    distanceMeters(center, coord) <= radiusMeters + toleranceMeters;

  const openLineTouches = coords => {
    if (!Array.isArray(coords) || coords.length === 0) return false;
    if (coords.length === 1) return within(coords[0]);
    for (let i = 0; i < coords.length - 1; i++) {
      if (within(coords[i]) || pointToSegmentMeters(center, coords[i], coords[i + 1]) <= radiusMeters + toleranceMeters) return true;
    }
    return within(coords[coords.length - 1]);
  };
  const ringTouches = ring => Array.isArray(ring) && ring.some((coord, i) =>
    within(coord) || pointToSegmentMeters(center, coord, ring[(i + 1) % ring.length]) <= radiusMeters + toleranceMeters
  );
  const polygonTouches = polygon => Array.isArray(polygon) && polygon.length > 0 &&
    (pointInPolygon([center.lon, center.lat], polygon) || polygon.some(ringTouches));

  const dispatch = geom => {
    if (!geom) return false;
    switch (geom.type) {
      case "Point": return within(geom.coordinates);
      case "MultiPoint": return Array.isArray(geom.coordinates) && geom.coordinates.some(within);
      case "LineString": return openLineTouches(geom.coordinates);
      case "MultiLineString": return Array.isArray(geom.coordinates) && geom.coordinates.some(openLineTouches);
      case "Polygon": return polygonTouches(geom.coordinates);
      case "MultiPolygon": return Array.isArray(geom.coordinates) && geom.coordinates.some(polygonTouches);
      case "GeometryCollection": return Array.isArray(geom.geometries) && geom.geometries.some(dispatch);
      default: return false;
    }
  };
  return dispatch(geometry);
}

export function filterFeatureCollectionToRadius(collection, center, radiusMeters) {
  if (!collection || !Array.isArray(collection.features)) throw new TypeError("FeatureCollection.features must be an array");
  const originalCount = collection.features.length;
  const features = collection.features.filter(feature => featureTouchesRadius(feature, center, radiusMeters));
  return { ...collection, features, filteredOutside: originalCount - features.length };
}
