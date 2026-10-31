export function getComparisonPeriods(year, monthValue, now = new Date()) {
  if (monthValue && monthValue !== "all") {
    const month = Number(monthValue) - 1;
    if (!Number.isInteger(month) || month < 0 || month > 11) throw new RangeError("monthValue must be 'all' or 01-12");
    const currentStart = new Date(year, month, 1);
    const currentEnd = new Date(year, month + 1, 1);
    const previousStart = new Date(year, month - 1, 1);
    return {
      currentStart,
      currentEnd,
      previousStart,
      previousEnd: currentStart,
      label: new Intl.DateTimeFormat("sv-SE", { month: "short", year: "numeric" }).format(currentStart)
        + " mot "
        + new Intl.DateTimeFormat("sv-SE", { month: "short", year: "numeric" }).format(previousStart)
    };
  }
  const currentStart = new Date(year, 0, 1);
  const currentEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const previousStart = new Date(year - 1, 0, 1);
  const previousEnd = new Date(year - 1, now.getMonth(), now.getDate() + 1);
  return {
    currentStart,
    currentEnd,
    previousStart,
    previousEnd,
    label: String(year) + " hittills mot " + String(year - 1) + " motsvarande period"
  };
}

export function compareValues(current, previous) {
  const difference = Number(current) - Number(previous);
  return {
    difference,
    percent: Number(previous) === 0 ? null : (difference / Number(previous)) * 100
  };
}

function signedArea(ring) {
  let area = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    area += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
  }
  return area / 2;
}

function pointInRing(point, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i], b = ring[j];
    if (((a[1] > point[1]) !== (b[1] > point[1]))
      && point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / ((b[1] - a[1]) || 1e-15) + a[0]) {
      inside = !inside;
    }
  }
  return inside;
}

export function arcgisGeometryToGeoJSON(geometry) {
  if (!geometry || typeof geometry !== "object") return null;
  if (geometry.type && Array.isArray(geometry.coordinates)) {
    return { type: geometry.type, coordinates: geometry.coordinates };
  }
  if (Array.isArray(geometry.rings) && geometry.rings.length) {
    const rings = geometry.rings.filter(ring => Array.isArray(ring) && ring.length >= 4);
    if (!rings.length) return null;
    let outers = rings.filter(ring => signedArea(ring) < 0);
    let holes = rings.filter(ring => signedArea(ring) >= 0);
    if (!outers.length) {
      outers = rings;
      holes = [];
    }
    const polygons = outers.map(ring => [ring]);
    for (const hole of holes) {
      const owner = polygons.find(poly => pointInRing(hole[0], poly[0]));
      if (owner) owner.push(hole);
      else polygons.push([hole]);
    }
    return polygons.length === 1
      ? { type: "Polygon", coordinates: polygons[0] }
      : { type: "MultiPolygon", coordinates: polygons };
  }
  if (Array.isArray(geometry.paths) && geometry.paths.length) {
    return geometry.paths.length === 1
      ? { type: "LineString", coordinates: geometry.paths[0] }
      : { type: "MultiLineString", coordinates: geometry.paths };
  }
  if (Array.isArray(geometry.points) && geometry.points.length) {
    return { type: "MultiPoint", coordinates: geometry.points };
  }
  if (Number.isFinite(geometry.x) && Number.isFinite(geometry.y)) {
    return { type: "Point", coordinates: [geometry.x, geometry.y] };
  }
  return null;
}
