export interface LonLat {
  lon: number;
  lat: number;
}

const MIN_SPAN = 0.8;

/** Projeção equiretangular (norte para cima) que encaixa os pontos no quadro, preservando proporções. */
export function project(points: LonLat[], width: number, height: number, padding: number): { x: number; y: number }[] {
  if (points.length === 0) return [];
  const lons = points.map((p) => p.lon);
  const lats = points.map((p) => p.lat);
  const midLat = (Math.min(...lats) + Math.max(...lats)) / 2;
  const kx = Math.cos((midLat * Math.PI) / 180);
  const minX = Math.min(...lons) * kx;
  const maxX = Math.max(...lons) * kx;
  const minY = Math.min(...lats);
  const maxY = Math.max(...lats);
  const spanX = Math.max(maxX - minX, MIN_SPAN);
  const spanY = Math.max(maxY - minY, MIN_SPAN);
  const scale = Math.min((width - 2 * padding) / spanX, (height - 2 * padding) / spanY);
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  return points.map((p) => ({
    x: width / 2 + (p.lon * kx - cx) * scale,
    y: height / 2 - (p.lat - cy) * scale,
  }));
}

export interface Label {
  x: number;
  y: number;
  anchor: "start" | "end";
}

const CHAR_W = 8.5;
const ASCENT = 13;
const DESCENT = 3;
const CANDIDATES: [number, number, "start" | "end"][] = [
  [12, 5, "start"], [-12, 5, "end"], [12, -9, "start"], [-12, -9, "end"],
  [12, 19, "start"], [-12, 19, "end"], [12, -23, "start"], [-12, -23, "end"],
  [12, 33, "start"], [-12, 33, "end"], [12, -37, "start"], [-12, -37, "end"],
];

type Box = { x0: number; x1: number; y0: number; y1: number };

function labelBox(l: Label, name: string): Box {
  const w = name.length * CHAR_W;
  const x0 = l.anchor === "start" ? l.x : l.x - w;
  return { x0, x1: x0 + w, y0: l.y - ASCENT, y1: l.y + DESCENT };
}

const hits = (a: Box, b: Box) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;

/** Posiciona rótulos sem sobreposição (guloso: tenta posições em volta do ponto, dentro do quadro). */
export function layoutLabels(points: { x: number; y: number }[], names: string[], width: number, height: number): Label[] {
  const dots: Box[] = points.map((p) => ({ x0: p.x - 6, x1: p.x + 6, y0: p.y - 6, y1: p.y + 6 }));
  const placed: Box[] = [];
  return points.map((p, i) => {
    const options = CANDIDATES.map(([dx, dy, anchor]) => ({ x: p.x + dx, y: p.y + dy, anchor }));
    const fits = (l: Label) => {
      const b = labelBox(l, names[i]);
      const inside = b.x0 >= 0 && b.x1 <= width && b.y0 >= 0 && b.y1 <= height;
      return inside && !placed.some((o) => hits(b, o)) && !dots.some((d, j) => j !== i && hits(b, d));
    };
    const chosen = options.find(fits) ?? options.find((l) => {
      const b = labelBox(l, names[i]);
      return b.x0 >= 0 && b.x1 <= width && b.y0 >= 0 && b.y1 <= height;
    }) ?? options[0];
    placed.push(labelBox(chosen, names[i]));
    return chosen;
  });
}
