import { layoutGenealogy, splitGenerations, type GenealogyLink, type GenealogyPerson, type PlacedPerson } from "@/lib/print";

const W = 720;
const CHUNK = 12;

function Part({ nodes, links, part, parts }: { nodes: PlacedPerson[]; links: GenealogyLink[]; part: number; parts: number }) {
  const top = Math.min(...nodes.map((n) => n.y));
  const byId = new Map(nodes.map((n) => [n.id, { ...n, y: 30 + n.y - top }]));
  const height = 30 + Math.max(...nodes.map((n) => n.y)) - top + 40;
  const width = Math.max(110, Math.min(140, W / Math.max(1, ...countPerLine(nodes)) - 10));
  return (
    <svg viewBox={`0 0 ${W} ${height}`} className="w-full" role="img" aria-label={`Árvore genealógica, parte ${part} de ${parts}`}>
      {links.map((l, i) => {
        const a = byId.get(l.from);
        const b = byId.get(l.to);
        if (!a || !b) return null;
        if (l.kind === "conjuge")
          return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#8c2f39" strokeWidth="1.2" strokeDasharray="3 3" />;
        const mid = a.y + 27;
        return <path key={i} d={`M ${a.x} ${a.y + 13} V ${mid} H ${b.x} V ${b.y - 13}`} fill="none" stroke="#a0802f" strokeWidth="1.3" />;
      })}
      {[...byId.values()].map((n) => (
        <g key={n.id}>
          <rect x={n.x - width / 2} y={n.y - 13} width={width} height={26} rx={13}
            fill={n.in_text ? "#4a3524" : "#faf6ea"} stroke={n.in_text ? "#4a3524" : "#a0802f"} strokeWidth="1" />
          <text x={n.x} y={n.y + 4.5} textAnchor="middle" fontSize={n.name.length > 16 ? 10.5 : 12.5}
            fontFamily="var(--font-gentium), serif" fontWeight="700" fontStyle={n.name_is_pt ? "normal" : "italic"}
            fill={n.in_text ? "#faf6ea" : "#2e2418"}>
            {n.name_is_pt ? n.name : `${n.name}*`}
          </text>
        </g>
      ))}
    </svg>
  );
}

function countPerLine(nodes: PlacedPerson[]): number[] {
  const lines = new Map<number, number>();
  for (const n of nodes) lines.set(n.y, (lines.get(n.y) ?? 0) + 1);
  return [...lines.values()];
}

export function GenealogyDiagram({ people, links }: { people: GenealogyPerson[]; links: GenealogyLink[] }) {
  const parts = splitGenerations(layoutGenealogy(people, links, W), CHUNK);
  return (
    <>
      {parts.map((nodes, i) => (
        <div key={i} className="ilustracao-parte">
          {parts.length > 1 && <p className="legenda">Parte {i + 1} de {parts.length}{i > 0 ? " (continua a geração anterior)" : ""}</p>}
          <Part nodes={nodes} links={links} part={i + 1} parts={parts.length} />
        </div>
      ))}
    </>
  );
}
