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

  // Cheap bounding-box rejection before testing every vertex and segment.
  const latPadding = (radiusMeters + toleranceMeters) / 110_540;
  const lonScale = Math.max(0.01, Math.cos(center.lat * Math.PI / 180));
  const lonPadding = (radiusMeters + toleranceMeters) / (111_320 * lonScale);
  const bbox = [Infinity, Infinity, -Infinity, -Infinity];
  const visitCoordinates = value => {
    if (!Array.isArray(value)) return;
    if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
      if (Number.isFinite(value[0]) && Number.isFinite(value[1])) {
        bbox[0] = Math.min(bbox[0], value[0]);
        bbox[1] = Math.min(bbox[1], value[1]);
        bbox[2] = Math.max(bbox[2], value[0]);
        bbox[3] = Math.max(bbox[3], value[1]);
      }
      return;
    }
    for (const child of value) visitCoordinates(child);
  };
  if (geometry.type === "GeometryCollection") {
    for (const item of geometry.geometries || []) visitCoordinates(item.coordinates);
  } else visitCoordinates(geometry.coordinates);
  if (bbox[0] !== Infinity &&
      (bbox[2] < center.lon - lonPadding || bbox[0] > center.lon + lonPadding ||
       bbox[3] < center.lat - latPadding || bbox[1] > center.lat + latPadding)) return false;

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
  const startedAt = globalThis.performance?.now?.() ?? Date.now();
  const originalCount = collection.features.length;
  const features = collection.features.filter(feature => featureTouchesRadius(feature, center, radiusMeters));
  const finishedAt = globalThis.performance?.now?.() ?? Date.now();
  return {
    ...collection,
    features,
    filteredOutside: originalCount - features.length,
    filterStats: {
      radiusMeters,
      inputFeatures: originalCount,
      outputFeatures: features.length,
      filteredOutside: originalCount - features.length,
      durationMs: Math.round((finishedAt - startedAt) * 100) / 100
    }
  };
}

/**
 * Clip polygon and multipolygon features to the selected circular search area.
 * Turf is injected by the browser caller so this module remains testable in Node.
 * Non-polygon geometries are retained unchanged; use the radius filter first.
 */
export function clipPolygonCollectionToRadius(collection, center, radiusMeters, turf) {
  if (!collection || !Array.isArray(collection.features)) throw new TypeError("FeatureCollection.features must be an array");
  if (!turf || typeof turf.circle !== "function" || typeof turf.intersect !== "function") {
    throw new TypeError("A Turf-compatible circle/intersect implementation is required");
  }
  const clipCircle = turf.circle([center.lon, center.lat], radiusMeters / 1000, {
    steps: 128,
    units: "kilometers"
  });
  const features = [];
  let clippedCount = 0;
  let polygonsConsidered = 0, polygonsClipped = 0, polygonsAlreadyInside = 0;
  const withinCircle = coord => Array.isArray(coord) && coord.length >= 2 &&
    Number.isFinite(coord[0]) && Number.isFinite(coord[1]) &&
    distanceMeters(center, coord) <= radiusMeters + 2;
  const hasCoordinates = value => {
    if (!Array.isArray(value)) return false;
    if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") return true;
    return value.some(hasCoordinates);
  };
  const allCoordinatesWithinCircle = value => {
    if (!Array.isArray(value)) return false;
    if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
      return withinCircle(value);
    }
    return value.every(allCoordinatesWithinCircle);
  };
  for (const feature of collection.features) {
    const type = feature?.geometry?.type;
    if (type !== "Polygon" && type !== "MultiPolygon") {
      features.push(feature);
      continue;
    }
    polygonsConsidered++;
    // A circle is convex: if every polygon vertex is inside it, every straight
    // edge is inside too. Avoid an expensive Turf intersection in this common case.
    if (hasCoordinates(feature.geometry.coordinates) && allCoordinatesWithinCircle(feature.geometry.coordinates)) {
      features.push(feature);
      polygonsAlreadyInside++;
      continue;
    }
    try {
      polygonsClipped++;
      const clipped = turf.intersect(turf.featureCollection([feature, clipCircle]));
      if (!clipped) {
        clippedCount++;
        continue;
      }
      features.push({ ...clipped, properties: feature.properties ?? {} });
      if (JSON.stringify(clipped.geometry) !== JSON.stringify(feature.geometry)) clippedCount++;
    } catch (error) {
      // Fail closed: don't draw an un-clipped polygon beyond the search circle.
      clippedCount++;
    }
  }
  return {
    ...collection,
    features,
    clippedOutside: clippedCount,
    clipStats: { polygonsConsidered, polygonsClipped, polygonsAlreadyInside }
  };
}
