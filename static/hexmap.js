// Hex geometry for the SVG map (pointy-top layout, axial coordinates).

export const HEX_SIZE = 52;

export function hexToPixel({ q, r }, size = HEX_SIZE) {
  return {
    x: size * Math.sqrt(3) * (q + r / 2),
    y: size * 1.5 * r
  };
}

export function hexCorners(center, size = HEX_SIZE) {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    points.push([
      center.x + size * Math.cos(angle),
      center.y + size * Math.sin(angle)
    ]);
  }
  return points;
}

export function boundingBox(systems, size = HEX_SIZE) {
  const points = systems.map(s => hexToPixel(s.hex, size));
  const xs = points.map(p => p.x);
  const ys = points.map(p => p.y);
  const pad = size * 1.6;
  return {
    minX: Math.min(...xs) - pad,
    minY: Math.min(...ys) - pad,
    width: Math.max(...xs) - Math.min(...xs) + pad * 2,
    height: Math.max(...ys) - Math.min(...ys) + pad * 2
  };
}
