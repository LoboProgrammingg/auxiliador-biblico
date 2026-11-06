import type { TimelineSection } from "@/types/api";

const W = 720;

export function TimelineDiagram({ reference, sections }: { reference: string; sections: TimelineSection[] }) {
  const first = sections[0].start;
  const last = sections[sections.length - 1].end;
  const total = Math.max(1, last - first + 1);
  return (
    <>
      <svg viewBox={`0 0 ${W} 64`} className="w-full" role="img" aria-label={`Linha do tempo de ${reference}`}>
        {sections.map((s, i) => {
          const x = ((s.start - first) / total) * W;
          const w = ((s.end - s.start + 1) / total) * W;
          return (
            <g key={i}>
              <rect x={x + 1} y={22} width={Math.max(w - 2, 2)} height={18} rx={3} fill={i % 2 === 0 ? "#e7d6a6" : "#d9c48c"} />
              <circle cx={x + Math.max(w, 22) / 2} cy={11} r={9} fill="#4a3524" />
              <text x={x + Math.max(w, 22) / 2} y={15} textAnchor="middle" fill="#faf6ea" fontSize="11" fontWeight="700">{i + 1}</text>
              <text x={x + 4} y={56} fill="#5a4a37" fontSize="11">v. {s.start}</text>
            </g>
          );
        })}
        <text x={W - 4} y={56} textAnchor="end" fill="#5a4a37" fontSize="11">v. {last}</text>
      </svg>
      <ol className="cenas">
        {sections.map((s, i) => (
          <li key={i}>
            <span className="cena-n">{i + 1}</span>
            <span className="cena-t">{s.title}</span>
            <span className="cena-v">v. {s.start}–{s.end}</span>
          </li>
        ))}
      </ol>
    </>
  );
}
