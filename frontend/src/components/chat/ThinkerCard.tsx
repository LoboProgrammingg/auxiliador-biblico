import type { Thinker } from "@/types/api";

/** Ideia de um pensador: visual próprio (sem aspas de Escritura, sem fonte de versículo) e rótulo fixo. */
export function ThinkerCard({ thinker }: { thinker: Thinker }) {
  const label = thinker.objection ? "Objeção cética — não é texto bíblico" : "Pensador — não é texto bíblico";
  return (
    <aside
      aria-label={label}
      className={`my-6 rounded-lg border border-dashed bg-pergaminho-claro/60 px-5 py-4 ${
        thinker.objection ? "border-vinho/60" : "border-oliva/70"
      }`}
    >
      <p
        className={`text-xs font-bold tracking-wider uppercase ${thinker.objection ? "text-vinho" : "text-oliva"}`}
      >
        {label}
      </p>
      <p className="mt-2 text-[1.02rem] leading-relaxed text-tinta">{thinker.text}</p>
      <p className="mt-2 flex flex-wrap items-baseline gap-x-2 text-sm text-tinta-suave">
        <span className="font-bold text-couro">{thinker.name}</span>
        <span>({thinker.period})</span>
        <span>· <cite>{thinker.work}</cite></span>
        <span className="rounded-full border border-borda px-2 text-xs">
          {thinker.kind === "citação" ? "citação conferida" : "paráfrase"}
        </span>
      </p>
    </aside>
  );
}
