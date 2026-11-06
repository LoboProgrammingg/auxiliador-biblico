"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BlockSkeleton } from "@/components/chat/Skeletons";
import { longDay } from "@/lib/diary";
import { progressPercent, studyPrompt, visibleDays } from "@/lib/plans";
import { API_URL, api } from "@/services/api";
import { useChat } from "@/stores/chat";
import type { PlanDetail, PlanSummary } from "@/types/api";

const OFFLINE = "Não consegui falar com a API. Confira se ela está rodando (scripts/api.sh).";

function Progress({ done, total }: { done: number; total: number }) {
  const pct = progressPercent(done, total);
  return (
    <div className="mt-2">
      <div className="h-2 overflow-hidden rounded-full bg-borda" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Progresso do plano">
        <div className="h-full rounded-full bg-gradient-to-r from-ouro to-oliva" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-1 text-xs text-tinta-suave">{done} de {total} dias lidos ({pct}%)</p>
    </div>
  );
}

function ActivePlan({ summary }: { summary: PlanSummary }) {
  const client = useQueryClient();
  const router = useRouter();
  const select = useChat((s) => s.select);
  const send = useChat((s) => s.send);
  const [expanded, setExpanded] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const key = ["plan", summary.id];
  const { data, isLoading } = useQuery({ queryKey: key, queryFn: () => api.plan(summary.id) });
  const mark = useMutation({
    mutationFn: ({ day, done }: { day: number; done: boolean }) => api.markPlanDay(summary.id, day, done),
    onMutate: async ({ day, done }) => {
      await client.cancelQueries({ queryKey: key });
      const previous = client.getQueryData<PlanDetail>(key);
      client.setQueryData<PlanDetail>(key, (p) =>
        p && { ...p, done: p.done + (done ? 1 : -1), days: p.days.map((d) => (d.day === day ? { ...d, done } : d)) },
      );
      return { previous };
    },
    onError: (_e, _v, ctx) => client.setQueryData(key, ctx?.previous),
    onSettled: () => client.invalidateQueries({ queryKey: ["plans"] }),
  });
  const remove = useMutation({
    mutationFn: () => api.deletePlan(summary.id),
    onSettled: () => client.invalidateQueries({ queryKey: ["plans"] }),
  });

  const today = data?.days[summary.today_day - 1];
  const study = async () => {
    if (!today) return;
    await select(null);
    router.push("/");
    void send(studyPrompt(summary.name, today.day, today.readings));
  };

  return (
    <li className="rounded-xl border border-ouro/40 bg-gradient-to-b from-[#fbf5e4] to-pergaminho-claro p-5 shadow-[0_20px_40px_-32px_rgba(74,53,36,0.7)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-escritura text-2xl font-bold text-couro">{summary.name}</h2>
        <span className="text-xs text-tinta-suave">desde {longDay(summary.started_on)}</span>
      </div>
      <Progress done={data?.done ?? summary.done} total={summary.total} />
      {isLoading && <BlockSkeleton lines={4} />}
      {today && (
        <div className="mt-4 rounded-lg border border-borda bg-pergaminho p-4">
          <p className="text-xs font-bold tracking-wider text-ouro uppercase">Leitura de hoje · dia {today.day}</p>
          <p className="mt-1 font-escritura text-xl text-couro">{today.readings.join(" · ")}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" onClick={() => void study()} className="rounded-full bg-couro px-4 py-1.5 text-sm font-bold text-pergaminho-claro">
              Estudar a leitura de hoje
            </button>
            {!today.done && (
              <button type="button" onClick={() => mark.mutate({ day: today.day, done: true })} className="rounded-full border border-oliva px-4 py-1.5 text-sm font-bold text-oliva hover:bg-oliva/10">
                Marcar como lida
              </button>
            )}
          </div>
        </div>
      )}
      {data && (
        <>
          <ol className="mt-4 divide-y divide-borda/70">
            {visibleDays(data.days, summary.today_day, expanded).map((d) => (
              <li key={d.day} className={`flex items-center gap-3 py-2 ${d.day === summary.today_day ? "font-bold" : ""}`}>
                <input
                  id={`d-${summary.id}-${d.day}`}
                  type="checkbox"
                  checked={d.done}
                  onChange={(e) => mark.mutate({ day: d.day, done: e.target.checked })}
                  className="h-4 w-4 accent-[#5d6b3a]"
                />
                <label htmlFor={`d-${summary.id}-${d.day}`} className="flex flex-1 items-baseline gap-3">
                  <span className="w-14 shrink-0 text-xs text-tinta-suave">dia {d.day}</span>
                  <span className={d.done ? "text-tinta-suave line-through decoration-ouro/60" : ""}>{d.readings.join(" · ")}</span>
                </label>
              </li>
            ))}
          </ol>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
            {data.days.length > 9 && (
              <button type="button" onClick={() => setExpanded((e) => !e)} className="font-bold text-couro underline decoration-ouro underline-offset-4">
                {expanded ? "Mostrar só perto de hoje" : `Ver todos os ${data.days.length} dias`}
              </button>
            )}
            <a href={`${API_URL}/api/v1/export/plano/${summary.id}.pdf`} className="font-bold text-couro underline decoration-ouro underline-offset-4">
              Baixar PDF do plano
            </a>
            {!confirming ? (
              <button type="button" onClick={() => setConfirming(true)} className="text-vinho hover:underline">Encerrar plano</button>
            ) : (
              <span className="flex items-center gap-2">
                <span className="text-vinho">Encerrar e apagar o progresso?</span>
                <button type="button" onClick={() => remove.mutate()} className="rounded-full bg-vinho px-3 py-1 font-bold text-pergaminho-claro">Sim</button>
                <button type="button" onClick={() => setConfirming(false)} className="rounded-full px-3 py-1">Não</button>
              </span>
            )}
          </div>
        </>
      )}
      {(mark.isError || remove.isError) && <p className="mt-2 text-sm text-vinho">{OFFLINE}</p>}
    </li>
  );
}

function Catalog({ active }: { active: Set<string> }) {
  const client = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["plan-catalog"], queryFn: api.planCatalog });
  const start = useMutation({
    mutationFn: (code: string) => api.startPlan(code),
    onSettled: () => client.invalidateQueries({ queryKey: ["plans"] }),
  });
  if (isLoading) return <BlockSkeleton lines={4} />;
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {data?.map((p) => (
        <li key={p.code} className="flex flex-col rounded-lg border border-borda bg-pergaminho-claro p-4">
          <h3 className="font-escritura text-lg font-bold text-couro">{p.name}</h3>
          <p className="text-xs text-tinta-suave">{p.days} dias</p>
          <p className="mt-1 flex-1 text-sm">{p.description}</p>
          <button
            type="button"
            disabled={active.has(p.code) || start.isPending}
            onClick={() => start.mutate(p.code)}
            className="mt-3 self-start rounded-full bg-couro px-4 py-1.5 text-sm font-bold text-pergaminho-claro disabled:opacity-40"
          >
            {active.has(p.code) ? "Em andamento" : "Começar hoje"}
          </button>
        </li>
      ))}
      {start.isError && <li className="text-sm text-vinho">{OFFLINE}</li>}
    </ul>
  );
}

export function PlansPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["plans"], queryFn: api.plans });
  return (
    <>
      <p className="mt-2 max-w-[65ch] text-tinta-suave">
        Escolha um plano, leia um pouco por dia e, quando quiser, peça um estudo da leitura de hoje.
      </p>
      {isLoading && <div className="mt-6"><BlockSkeleton lines={5} /></div>}
      {isError && <p className="mt-6 text-vinho">{OFFLINE}</p>}
      {data && data.length > 0 && (
        <ul className="mt-6 space-y-5">{data.map((p) => <ActivePlan key={p.id} summary={p} />)}</ul>
      )}
      <h2 className="mt-10 mb-3 font-escritura text-xl font-bold text-couro">Planos disponíveis</h2>
      <Catalog active={new Set(data?.map((p) => p.code))} />
    </>
  );
}
