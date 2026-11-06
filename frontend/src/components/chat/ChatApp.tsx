"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { matchShortcut } from "@/lib/shortcuts";
import { API_URL } from "@/services/api";
import { useChat } from "@/stores/chat";
import { Composer } from "./Composer";
import { DailyWordCard } from "./DailyWordCard";
import { Divider } from "./Ornament";
import { MessageView } from "./MessageView";
import { BlockSkeleton } from "./Skeletons";
import { Sidebar } from "./Sidebar";
import { StatusLine } from "./StatusLine";
import { VersePopup } from "./VersePopup";
import { VERSE_SEARCH_ID } from "./VerseSearch";

const STARTERS = [
  "Estou com medo de não conseguir pagar as contas deste mês.",
  "Errei de novo e sinto que me afastei de Jesus. O que eu faço?",
  "Interprete para mim o capítulo 1 de João.",
];

function Welcome() {
  const send = useChat((s) => s.send);
  return (
    <div className="mx-auto mt-[12vh] max-w-xl">
      <h1 className="font-escritura text-[2.1rem] leading-tight font-bold text-couro">Sobre o que você quer conversar hoje?</h1>
      <Divider className="mt-3" />
      <p className="mt-2 text-tinta-suave">
        Conte o que está vivendo, peça um estudo ou uma palavra para o dia. Eu lembro das nossas conversas.
      </p>
      <ul className="mt-6 space-y-2">
        {STARTERS.map((s) => (
          <li key={s}>
            <button
              type="button"
              onClick={() => void send(s)}
              className="w-full rounded-lg border border-borda bg-pergaminho-claro px-4 py-3 text-left hover:border-ouro"
            >
              {s}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ChatApp() {
  const { messages, loading, streaming, daily, conversationId, focus, toggleFocus, select } = useChat();
  const queryClient = useQueryClient();
  const bottom = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    if (!streaming) void queryClient.invalidateQueries({ queryKey: ["conversations"] });
  }, [streaming, queryClient]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const action = matchShortcut(e);
      if (!action) return;
      e.preventDefault();
      if (action === "nova") void select(null);
      if (action === "foco") {
        setMenuOpen(false);
        toggleFocus();
      }
      if (action === "compor") document.getElementById("mensagem")?.focus();
      if (action === "buscar") {
        if (focus) toggleFocus();
        setMenuOpen(true);
        setTimeout(() => document.getElementById(VERSE_SEARCH_ID)?.focus(), 0);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [select, toggleFocus, focus]);

  return (
    <div className={`grid h-dvh ${focus ? "foco" : "md:grid-cols-[17rem_1fr]"}`}>
      <div className={`${menuOpen ? "fixed inset-y-0 left-0 z-30 w-72" : "hidden"} ${focus ? "" : "md:static md:block"}`}>
        <Sidebar onNavigate={() => setMenuOpen(false)} />
      </div>
      <main className="flex min-h-0 flex-col">
        <header className="flex items-center gap-3 border-b border-borda px-4 py-2 md:hidden">
          <button type="button" onClick={() => setMenuOpen((o) => !o)} className="rounded px-2 py-1 text-sm font-bold text-couro">
            Menu
          </button>
          <p className="font-escritura font-bold text-couro">Auxiliador Bíblico</p>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl space-y-7 px-5 py-8">
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  toggleFocus();
                }}
                aria-pressed={focus}
                className="rounded-full border border-borda px-3 py-1 text-sm text-couro hover:border-ouro"
                title="Alt+F"
              >
                {focus ? "Sair do modo foco" : "Modo foco"}
              </button>
              {conversationId && messages.length > 0 && !streaming && (
                <a
                  href={`${API_URL}/api/v1/export/conversa/${conversationId}.pdf`}
                  className="rounded-full border border-borda px-3 py-1 text-sm font-bold text-couro hover:border-ouro hover:bg-ouro-claro/40"
                >
                  Baixar PDF do estudo
                </a>
              )}
            </div>
            {loading && <BlockSkeleton lines={6} />}
            <DailyWordCard />
            {!loading && messages.length === 0 && daily.status === "idle" && <Welcome />}
            {messages.map((m) => (
              <MessageView key={m.key} message={m} />
            ))}
            <StatusLine />
            <div ref={bottom} />
          </div>
        </div>
        <Composer />
      </main>
      <VersePopup />
    </div>
  );
}
