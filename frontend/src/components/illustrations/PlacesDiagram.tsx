import { layoutLabels, project } from "@/lib/geo";

const W = 640;
const H = 380;
const PAD = 56;

export interface DiagramPlace {
  name: string;
  lon: number;
  lat: number;
}

/** Mapa em SVG dos lugares do banco (OpenBible, CC BY); com `route`, numera e liga na ordem de menção. */
export function PlacesDiagram({ places, route = false, label }: { places: DiagramPlace[]; route?: boolean; label: string }) {
  const points = project(places, W, H, PAD);
  const labels = layoutLabels(points, places.map((p, i) => (route ? `${i + 1}. ${p.name}` : p.name)), W, H);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={label}>
      <defs>
        <marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="#a0802f" />
        </marker>
      </defs>
      <rect x="0" y="0" width={W} height={H} rx="10" fill="#fbf6e8" stroke="#dccfb0" />
      {[0.25, 0.5, 0.75].map((f) => (
        <g key={f} stroke="#e8dcc0" strokeWidth="0.8" strokeDasharray="2 5">
          <line x1={W * f} y1="12" x2={W * f} y2={H - 12} />
          <line x1="12" y1={H * f} x2={W - 12} y2={H * f} />
        </g>
      ))}
      <g transform={`translate(${W - 34}, 34)`} fill="#5a4a37">
        <path d="M0 -14 L5 4 L0 0 L-5 4 Z" />
        <text y="18" textAnchor="middle" fontSize="11" fontWeight="700">N</text>
      </g>
      {route &&
        points.slice(1).map((p, i) => {
          const a = points[i];
          const dx = p.x - a.x;
          const dy = p.y - a.y;
          const len = Math.hypot(dx, dy) || 1;
          const pull = Math.min(10, len / 3);
          return (
            <path key={`r${i}`} d={`M ${a.x + (dx / len) * pull} ${a.y + (dy / len) * pull} Q ${(a.x + p.x) / 2 - dy * 0.12} ${(a.y + p.y) / 2 + dx * 0.12} ${p.x - (dx / len) * pull} ${p.y - (dy / len) * pull}`}
              fill="none" stroke="#a0802f" strokeWidth="1.6" strokeDasharray="5 4" markerEnd="url(#seta)" />
          );
        })}
      {places.map((p, i) => {
        const { x, y } = points[i];
        const l = labels[i];
        return (
          <g key={`${p.name}-${i}`}>
            <circle cx={x} cy={y} r={9} fill="#e7d6a6" opacity="0.75" />
            <circle cx={x} cy={y} r={4.5} fill="#4a3524" />
            <text x={l.x} y={l.y} textAnchor={l.anchor} fill="#2e2418" fontSize="15" fontWeight="700"
              fontFamily="var(--font-gentium), serif" paintOrder="stroke" stroke="#fbf6e8" strokeWidth="4">
              {route ? `${i + 1}. ${p.name}` : p.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
