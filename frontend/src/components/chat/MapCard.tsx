"use client";

import { layoutLabels, project } from "@/lib/geo";
import { useChat } from "@/stores/chat";
import type { MapPlace } from "@/types/api";

const W = 640;
const H = 380;
const PAD = 56;

export function MapCard({ reference, places }: { reference: string; places: MapPlace[] }) {
  const openPopup = useChat((s) => s.openPopup);
  const points = project(places, W, H, PAD);
  const labels = layoutLabels(points, places.map((p) => p.name), W, H);
  const open = (p: MapPlace) => openPopup({ reference: `${reference}:${p.verses[0]}`, translation: "vfl" });

  return (
    <figure className="my-6 rounded-lg border border-borda bg-pergaminho-claro/90 px-5 pt-4 pb-4 shadow-[0_1px_0_#e7dcc3,0_12px_30px_-22px_rgba(74,53,36,0.55)]">
      <figcaption className="font-escritura text-lg font-bold text-couro">Onde acontece</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" role="img" aria-label={`Mapa dos lugares de ${reference}`}>
        <defs>
          <radialGradient id="papel" cx="50%" cy="45%" r="70%">
            <stop offset="0%" stopColor="#fbf6e8" />
            <stop offset="100%" stopColor="#efe4c8" />
          </radialGradient>
        </defs>
        <rect x="0" y="0" width={W} height={H} rx="10" fill="url(#papel)" stroke="#dccfb0" />
        {[0.25, 0.5, 0.75].map((f) => (
          <g key={f} stroke="#e2d4b2" strokeWidth="0.8" strokeDasharray="2 5">
            <line x1={W * f} y1="12" x2={W * f} y2={H - 12} />
            <line x1="12" y1={H * f} x2={W - 12} y2={H * f} />
          </g>
        ))}
        <g transform={`translate(${W - 34}, 34)`} className="fill-tinta-suave">
          <path d="M0 -14 L5 4 L0 0 L-5 4 Z" />
          <text y="18" textAnchor="middle" className="text-[11px] font-bold">N</text>
        </g>
        {places.map((p, i) => {
          const { x, y } = points[i];
          const label = labels[i];
          return (
            <g key={`${p.name}-${i}`} className="cursor-pointer" onClick={() => open(p)}>
              <circle cx={x} cy={y} r={9} className="fill-ouro-claro" opacity="0.7" />
              <circle cx={x} cy={y} r={4.5} className="fill-couro" />
              <line x1={x} y1={y} x2={label.anchor === "start" ? label.x - 3 : label.x + 3} y2={label.y - 5}
                stroke="#a0802f" strokeWidth="0.8" opacity="0.6" />
              <text x={label.x} y={label.y} textAnchor={label.anchor}
                className="fill-tinta font-escritura text-[15px] font-bold" paintOrder="stroke" stroke="#fbf6e8" strokeWidth="4">
                {p.name}
              </text>
            </g>
          );
        })}
      </svg>
      <ul className="!ml-0 mt-3 flex !list-none flex-wrap gap-x-5 gap-y-1 text-sm">
        {places.map((p, i) => (
          <li key={`${p.name}-l-${i}`}>
            <button type="button" onClick={() => open(p)} className="hover:underline">
              <span className="font-bold text-couro">{p.name}</span>{" "}
              <span className="text-tinta-suave">v. {p.verses.join(", ")}</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-tinta-suave">
        Posições aproximadas dos lugares citados. Dados de OpenBible.info, licença CC BY 4.0.
      </p>
    </figure>
  );
}
