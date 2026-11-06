import { chiasmRows } from "@/lib/illustrations";
import type { ChiasmPart } from "@/types/api";

const ROW = 40;
const INDENT = 34;
const LEFT = 26;

/** Estrutura em espelho desenhada em SVG; só versículos conferidos no banco. */
export function ChiasmDiagram({ parts, onOpen }: { parts: ChiasmPart[]; onOpen?: (p: ChiasmPart) => void }) {
  const rows = chiasmRows(parts.map((p) => p.label));
  const height = rows.length * ROW;
  const maxDepth = Math.max(...rows.map((r) => r.depth));
  return (
    <svg viewBox={`0 0 720 ${height}`} className="w-full" role="img" aria-label="Estrutura em espelho">
      {rows.map((r, i) =>
        r.pair !== null && r.pair > i ? (
          <path
            key={`b${i}`}
            d={`M ${LEFT + r.depth * INDENT + 6} ${i * ROW + ROW / 2} H ${LEFT + r.depth * INDENT - 8 - (maxDepth - r.depth) * 2} V ${r.pair * ROW + ROW / 2} H ${LEFT + r.depth * INDENT + 6}`}
            className="fill-none stroke-ouro"
            strokeWidth={1.4}
          />
        ) : null,
      )}
      {parts.map((p, i) => {
        const x = LEFT + rows[i].depth * INDENT + 10;
        const center = rows[i].pair === null;
        return (
          <g key={i} className={onOpen ? "cursor-pointer" : undefined} onClick={onOpen ? () => onOpen(p) : undefined}>
            <rect x={x} y={i * ROW + 5} width={720 - x - 4} height={ROW - 10} rx={4}
              className={center ? "fill-ouro-claro" : i % 2 === 0 ? "fill-pergaminho" : "fill-[#f3e8cc]"} />
            <text x={x + 10} y={i * ROW + ROW / 2 + 5} className="fill-couro font-escritura text-[15px] font-bold">{p.label}</text>
            <text x={x + 42} y={i * ROW + ROW / 2 + 5} className="fill-tinta font-escritura text-[14px]">{p.title}</text>
            <text x={716 - 8} y={i * ROW + ROW / 2 + 5} textAnchor="end" className="fill-tinta-suave text-[11px]">
              v. {p.start === p.end ? p.start : `${p.start}–${p.end}`}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
