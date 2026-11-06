"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BlockSkeleton } from "@/components/chat/Skeletons";
import { sortMemories, topicTitle } from "@/lib/memory";
import { api } from "@/services/api";
import type { MemoryItem } from "@/types/api";

function MemoryCard({ item }: { item: MemoryItem }) {
  const client = useQueryClient();
  const [draft, setDraft] = useState(item.content);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => api.saveMemory(item.topic, draft),
    onMutate: () => setError(null),
    onError: () => setError("Não consegui salvar. Confira se a API está rodando."),
    onSettled: () => client.invalidateQueries({ queryKey: ["memories"] }),
  });
  const remove = useMutation({
    mutationFn: () => api.deleteMemory(item.topic),
    onMutate: async () => {
      await client.cancelQueries({ queryKey: ["memories"] });
      const previous = client.getQueryData<MemoryItem[]>(["memories"]);
      client.setQueryData<MemoryItem[]>(["memories"], (items) => items?.filter((i) => i.topic !== item.topic));
      return { previous };
    },
    onError: (_e, _v, ctx) => {
      client.setQueryData(["memories"], ctx?.previous);
      setError("Não consegui apagar. Tente de novo.");
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["memories"] }),
  });

  return (
    <li className="rounded-lg border border-borda bg-pergaminho-claro p-4">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-escritura text-lg font-bold text-couro">{topicTitle(item.topic)}</h2>
        <time className="text-xs text-tinta-suave" dateTime={item.updated_at}>
          {new Date(item.updated_at).toLocaleDateString("pt-BR")}
        </time>
      </div>
      <label htmlFor={`m-${item.topic}`} className="sr-only">Conteúdo de {topicTitle(item.topic)}</label>
      <textarea
        id={`m-${item.topic}`}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={Math.min(10, Math.max(3, draft.split("\n").length + 1))}
        maxLength={4000}
        className="mt-2 w-full rounded border border-borda bg-pergaminho p-2 leading-relaxed"
      />
      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
        <button
          type="button"
          disabled={draft === item.content || !draft.trim() || save.isPending}
          onClick={() => save.mutate()}
          className="rounded-full bg-couro px-4 py-1.5 font-bold text-pergaminho-claro disabled:opacity-40"
        >
          {save.isPending ? "Salvando…" : "Salvar"}
        </button>
        {!confirming ? (
          <button type="button" onClick={() => setConfirming(true)} className="rounded-full px-3 py-1.5 font-bold text-vinho hover:bg-vinho/10">
            Apagar
          </button>
        ) : (
          <span className="flex items-center gap-2">
            <span className="text-vinho">Apagar esta memória?</span>
            <button type="button" onClick={() => remove.mutate()} className="rounded-full bg-vinho px-3 py-1.5 font-bold text-pergaminho-claro">
              Sim, apagar
            </button>
            <button type="button" onClick={() => setConfirming(false)} className="rounded-full px-3 py-1.5">
              Cancelar
            </button>
          </span>
        )}
        {error && <span className="text-vinho">{error}</span>}
      </div>
    </li>
  );
}

export function MemoryPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["memories"], queryFn: api.memories });
  return (
    <>
      <p className="mt-2 max-w-[65ch] text-tinta-suave">
        O que o auxiliador lembra de você para acompanhar suas conversas. Fica só neste computador. Você pode
        corrigir ou apagar qualquer item.
      </p>
      <div className="mt-6">
        {isLoading && <BlockSkeleton lines={5} />}
        {isError && <p className="text-vinho">Não consegui carregar a memória. Confira se a API está rodando.</p>}
        {data && data.length === 0 && (
          <p className="rounded-lg border border-dashed border-borda p-6 text-tinta-suave">
            Ainda não guardei nada sobre você. Converse comigo e eu vou lembrando do que for importante.
          </p>
        )}
        {data && data.length > 0 && (
          <ul className="space-y-4">
            {sortMemories(data).map((item) => (
              <MemoryCard key={item.topic} item={item} />
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
