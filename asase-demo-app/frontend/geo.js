"use strict";
// Coordinates use [longitude, latitude] in GeoJSON, [latitude, longitude] in the API.
const ghanaRings = GHANA_BOUNDARY.features[0].geometry.coordinates;
function ringContains(ring, x, y) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [ax, ay] = ring[j],
      [bx, by] = ring[i];
    const cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax);
    if (
      Math.abs(cross) < 1e-12 &&
      x >= Math.min(ax, bx) &&
      x <= Math.max(ax, bx) &&
      y >= Math.min(ay, by) &&
      y <= Math.max(ay, by)
    )
      return true;
    if (ay > y !== by > y && x < ((bx - ax) * (y - ay)) / (by - ay) + ax)
      inside = !inside;
  }
  return inside;
}
function inGhana(point) {
  if (!Array.isArray(point) || !point.every(Number.isFinite)) return false;
  const [y, x] = point;
  return (
    ringContains(ghanaRings[0], x, y) &&
    !ghanaRings.slice(1).some((r) => ringContains(r, x, y))
  );
}
// A boundary segment entering the open rectangle means the whole area is not covered.
// Checking only the corners would allow rectangles to cross a concave border.
function segmentEntersBox(a, b, box) {
  const [south, west, north, east] = box;
  let lo = 0,
    hi = 1;
  for (const [p, d, min, max] of [
    [a[0], b[0] - a[0], west, east],
    [a[1], b[1] - a[1], south, north],
  ]) {
    if (d === 0) {
      if (p <= min || p >= max) return false;
    } else {
      const u = (min - p) / d,
        v = (max - p) / d;
      lo = Math.max(lo, Math.min(u, v));
      hi = Math.min(hi, Math.max(u, v));
    }
  }
  return lo < hi;
}
function boxInGhana(b) {
  if (
    !Array.isArray(b) ||
    b.length !== 4 ||
    !b.every(Number.isFinite) ||
    b[0] >= b[2] ||
    b[1] >= b[3]
  )
    return false;
  if (
    ![
      [b[0], b[1]],
      [b[0], b[3]],
      [b[2], b[1]],
      [b[2], b[3]],
    ].every(inGhana)
  )
    return false;
  return !ghanaRings.some((r) =>
    r.some((p, i) => i > 0 && segmentEntersBox(r[i - 1], p, b)),
  );
}
// Approximate surface of a lat/lon rectangle, mean Earth radius; not cadastral area.
function hectares(b) {
  const rad = Math.PI / 180;
  return (
    (6371008.8 ** 2 *
      (b[3] - b[1]) *
      rad *
      (Math.sin(b[2] * rad) - Math.sin(b[0] * rad))) /
    10000
  );
}
