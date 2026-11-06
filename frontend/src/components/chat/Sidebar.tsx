"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/services/api";
import { useChat } from "@/stores/chat";
import { Emblem } from "./Ornament";
import { LineSkeleton } from "./Skeletons";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const conversationId = useChat((s) => s.conversationId);
  const select = useChat((s) => s.select);
  const { data, isLoading } = useQuery({ queryKey: ["conversations"], queryFn: api.conversations });
  const client = useQueryClient();
  const [confirming, setConfirming] = useState<string | null>(null);
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: (_r, id) => {
      if (id === conversationId) void select(null);
      setConfirming(null);
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["conversations"] }),
  });

  return (
    <nav className="flex h-full flex-col bg-gradient-to-b from-[#4f3826] via-couro to-[#3a2a1c] text-pergaminho-claro shadow-[inset_-1px_0_0_rgba(160,128,47,0.35)]" aria-label="Conversas">
      <div className="flex items-center gap-2.5 px-5 pt-6 pb-5">
        <Emblem className="text-ouro-claro" />
        <p className="font-escritura text-xl leading-tight font-bold">Auxiliador<br />Bíblico</p>
      </div>
      <div className="px-3">
        <button
          type="button"
          onClick={() => {
            void select(null);
            onNavigate?.();
          }}
          className="w-full rounded-lg border border-pergaminho-claro/25 px-3 py-2 text-left text-sm font-bold hover:bg-couro-claro"
        >
          + Nova conversa
        </button>
      </div>
      <ul className="mt-3 flex-1 space-y-0.5 overflow-y-auto px-3">
        {isLoading && [1, 2, 3].map((i) => <li key={i} className="px-3 py-2"><LineSkeleton width="80%" /></li>)}
        {data?.map((c) => (
          <li key={c.id} className="group relative">
            {confirming === c.id ? (
              <div className="flex items-center gap-1 rounded-lg bg-couro-claro px-2 py-1.5 text-sm">
                <span className="flex-1">Apagar conversa?</span>
                <button type="button" onClick={() => remove.mutate(c.id)} className="rounded px-2 py-0.5 font-bold text-ouro-claro hover:bg-vinho">
                  Apagar
                </button>
                <button type="button" onClick={() => setConfirming(null)} className="rounded px-2 py-0.5 hover:bg-couro">
                  Cancelar
                </button>
              </div>
            ) : (
            <button
              type="button"
              onClick={() => {
                void select(c.id);
                onNavigate?.();
              }}
              aria-current={c.id === conversationId ? "page" : undefined}
              className={`w-full truncate rounded-lg py-2 pr-8 pl-3 text-left text-sm ${c.id === conversationId ? "bg-couro-claro" : "hover:bg-couro-claro/60"}`}
            >
              {c.title}
            </button>
            )}
            {confirming !== c.id && (
              <button
                type="button"
                aria-label={`Apagar conversa ${c.title}`}
                onClick={() => setConfirming(c.id)}
                className="absolute top-1.5 right-1.5 hidden rounded px-1.5 text-sm text-pergaminho-claro/70 group-hover:block focus-visible:block hover:bg-vinho hover:text-pergaminho-claro"
              >
                ×
              </button>
            )}
          </li>
        ))}
      </ul>
      <div className="space-y-0.5 border-t border-pergaminho-claro/15 px-3 py-3 text-sm">
        <Link href="/memoria" className="block rounded-lg px-3 py-2 hover:bg-couro-claro/60">🧠 Memória</Link>
        <Link href="/sobre" className="block rounded-lg px-3 py-2 hover:bg-couro-claro/60">Sobre</Link>
      </div>
    </nav>
  );
}
