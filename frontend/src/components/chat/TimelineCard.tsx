"use client";

import { useChat } from "@/stores/chat";
import type { TimelineSection } from "@/types/api";

const W = 720;

export function TimelineCard({ reference, book, sections }: { reference: string; book: string; sections: TimelineSection[] }) {
  const openPopup = useChat((s) => s.openPopup);
  const chapter = reference.split(" ").slice(1).join(" ");
  const first = sections[0].start;
  const last = sections[sections.length - 1].end;
  const total = Math.max(1, last - first + 1);
  const open = (s: TimelineSection) => openPopup({ reference: `${reference}:${s.start}-${s.end}`, translation: "vfl" });

  const bars = sections.map((s, i) => ({
    s,
    i,
    x: ((s.start - first) / total) * W,
    w: ((s.end - s.start + 1) / total) * W,
  }));

  return (
    <figure className="my-6 rounded-lg border border-borda bg-pergaminho-claro/90 px-5 pt-4 pb-5 shadow-[0_1px_0_#e7dcc3,0_12px_30px_-22px_rgba(74,53,36,0.55)]">
      <figcaption className="font-escritura text-lg font-bold text-couro">
        {book} {chapter}: as cenas em ordem
      </figcaption>
      <svg viewBox={`0 0 ${W} 64`} className="mt-3 w-full" role="img" aria-label={`Linha do tempo de ${reference}`}>
        {bars.map(({ s, i, x: bx, w }) => (
          <g key={i} className="cursor-pointer" onClick={() => open(s)}>
            <rect x={bx + 1} y={22} width={Math.max(w - 2, 2)} height={18} rx={3}
              className={i % 2 === 0 ? "fill-ouro-claro" : "fill-[#d9c48c]"} />
            <circle cx={bx + Math.max(w, 22) / 2} cy={11} r={9} className="fill-couro" />
            <text x={bx + Math.max(w, 22) / 2} y={15} textAnchor="middle" className="fill-pergaminho-claro text-[11px] font-bold">
              {i + 1}
            </text>
            <text x={bx + 4} y={56} className="fill-tinta-suave text-[11px]">
              v. {s.start}
            </text>
          </g>
        ))}
        <text x={W - 4} y={56} textAnchor="end" className="fill-tinta-suave text-[11px]">v. {last}</text>
      </svg>
      <ol className="!ml-0 mt-3 !list-none divide-y divide-borda/60">
        {sections.map((s, i) => (
          <li key={i}>
            <button type="button" onClick={() => open(s)}
              className="flex w-full items-baseline gap-3 rounded px-2 py-1.5 text-left hover:bg-ouro-claro/40">
              <span className="w-5 shrink-0 font-escritura font-bold text-ouro">{i + 1}</span>
              <span className="min-w-0 flex-1 font-escritura text-[1.05rem] text-tinta">{s.title}</span>
              <span className="shrink-0 text-xs text-tinta-suave">v. {s.start}–{s.end}</span>
            </button>
          </li>
        ))}
      </ol>
    </figure>
  );
}
