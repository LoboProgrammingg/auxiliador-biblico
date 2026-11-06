import { notFound } from "next/navigation";
import { Cover } from "@/components/print/Cover";
import { PrintDocument } from "@/components/print/PrintDocument";
import { longDay } from "@/lib/diary";
import { progressPercent } from "@/lib/plans";
import { fetchApi } from "@/lib/server-api";
import type { PlanDetail } from "@/types/api";

export default async function PrintPlan({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const plan = await fetchApi<PlanDetail>(`/plans/${id}`);
  if (!plan) notFound();
  const pct = progressPercent(plan.done, plan.total);
  return (
    <PrintDocument pdfPath={`plano/${id}`}>
      <Cover eyebrow="Plano de leitura" title={plan.name} subtitle={plan.description} date={`Começou em ${longDay(plan.started_on)}`} />
      <section className="secao plano">
        <h2>Como usar</h2>
        <p>
          Leia a passagem de cada dia e marque o quadrado. Use a margem para anotar o que Deus falar com você. No Auxiliador,
          o botão «Estudar a leitura de hoje» abre um estudo guiado do trecho.
        </p>
        <div className="progresso">
          <div className="progresso-barra"><div style={{ width: `${pct}%` }} /></div>
          <p>{plan.done} de {plan.total} dias lidos ({pct}%)</p>
        </div>
        <ol className="dias">
          {plan.days.map((d) => (
            <li key={d.day} className={d.done ? "lido" : undefined}>
              <span className="caixa" aria-hidden>{d.done ? "✓" : ""}</span>
              <span className="dia">Dia {d.day}</span>
              <span className="leitura">{d.readings.join(" · ")}</span>
            </li>
          ))}
        </ol>
      </section>
    </PrintDocument>
  );
}
