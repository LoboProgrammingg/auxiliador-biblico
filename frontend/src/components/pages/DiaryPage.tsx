"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BlockSkeleton } from "@/components/chat/Skeletons";
import { VersePopup } from "@/components/chat/VersePopup";
import { groupPrayers, longDay } from "@/lib/diary";
import { api } from "@/services/api";
import { useChat } from "@/stores/chat";
import type { Prayer, VerseNote } from "@/types/api";

const TABS = [
  { id: "palavras", label: "Palavras do dia" },
  { id: "oracoes", label: "Orações" },
  { id: "anotacoes", label: "Anotações" },
] as const;
type Tab = (typeof TABS)[number]["id"];

const OFFLINE = "Não consegui falar com a API. Confira se ela está rodando (scripts/api.sh).";

function RefButton({ reference }: { reference: string }) {
  const openPopup = useChat((s) => s.openPopup);
  return (
    <button
      type="button"
      onClick={() => openPopup({ reference, translation: "vfl" })}
      className="font-escritura font-bold text-couro underline decoration-ouro decoration-dotted underline-offset-4 hover:decoration-solid"
    >
      {reference}
    </button>
  );
}

function Words() {
  const router = useRouter();
  const select = useChat((s) => s.select);
  const { data, isLoading, isError } = useQuery({ queryKey: ["daily-words"], queryFn: api.dailyWords });
  if (isLoading) return <BlockSkeleton lines={5} />;
  if (isError) return <p className="text-vinho">{OFFLINE}</p>;
  if (!data?.length)
    return <Empty>Ainda não há palavras guardadas. Use ✨ Uma palavra pra mim na conversa.</Empty>;
  return (
    <ol className="relative space-y-3 border-l-2 border-ouro/40 pl-6">
      {data.map((w) => (
        <li key={w.day} className="relative">
          <span aria-hidden className="absolute top-2 -left-[1.95rem] h-3 w-3 rotate-45 border border-ouro bg-pergaminho-claro" />
          <p className="text-sm text-tinta-suave first-letter:uppercase">{longDay(w.day)}</p>
          <div className="flex flex-wrap items-baseline gap-x-4">
            {w.reference ? <RefButton reference={w.reference} /> : <span className="text-tinta-suave">sem passagem</span>}
            <button
              type="button"
              onClick={() => {
                void select(w.conversation_id);
                router.push("/");
              }}
              className="text-sm text-oliva underline-offset-4 hover:underline"
            >
              reler a palavra completa
            </button>
          </div>
        </li>
      ))}
    </ol>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg border border-dashed border-borda p-6 text-tinta-suave">{children}</p>;
}

function NewPrayer() {
  const client = useQueryClient();
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const create = useMutation({
    mutationFn: () => api.createPrayer(title.trim(), details.trim() || null),
    onSuccess: () => {
      setTitle("");
      setDetails("");
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["prayers"] }),
  });
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (title.trim()) create.mutate();
      }}
      className="rounded-lg border border-borda bg-pergaminho-claro p-4"
    >
      <label htmlFor="prayer-title" className="font-escritura text-lg font-bold text-couro">Novo pedido de oração</label>
      <input
        id="prayer-title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={120}
        placeholder="Pelo que você quer orar?"
        className="mt-2 w-full rounded border border-borda bg-pergaminho p-2"
      />
      <label htmlFor="prayer-details" className="sr-only">Detalhes</label>
      <textarea
        id="prayer-details"
        value={details}
        onChange={(e) => setDetails(e.target.value)}
        rows={2}
        maxLength={4000}
        placeholder="Detalhes (opcional)"
        className="mt-2 w-full rounded border border-borda bg-pergaminho p-2"
      />
      <div className="mt-2 flex items-center gap-3">
        <button type="submit" disabled={!title.trim() || create.isPending} className="rounded-full bg-couro px-4 py-1.5 text-sm font-bold text-pergaminho-claro disabled:opacity-40">
          {create.isPending ? "Guardando…" : "Guardar pedido"}
        </button>
        {create.isError && <span className="text-sm text-vinho">{OFFLINE}</span>}
      </div>
    </form>
  );
}

function PrayerCard({ prayer }: { prayer: Prayer }) {
  const client = useQueryClient();
  const [answering, setAnswering] = useState(false);
  const [note, setNote] = useState(prayer.answer_note ?? "");
  const [confirming, setConfirming] = useState(false);
  const change = useMutation({
    mutationFn: (next: Pick<Prayer, "status" | "answer_note">) => api.updatePrayer({ ...prayer, ...next }),
    onMutate: async (next) => {
      await client.cancelQueries({ queryKey: ["prayers"] });
      const previous = client.getQueryData<Prayer[]>(["prayers"]);
      const answeredAt = next.status === "respondido" ? (prayer.answered_at ?? new Date().toISOString()) : null;
      client.setQueryData<Prayer[]>(["prayers"], (items) =>
        items?.map((p) => (p.id === prayer.id ? { ...p, ...next, answered_at: answeredAt } : p)),
      );
      return { previous };
    },
    onError: (_e, _v, ctx) => client.setQueryData(["prayers"], ctx?.previous),
    onSettled: () => client.invalidateQueries({ queryKey: ["prayers"] }),
  });
  const remove = useMutation({
    mutationFn: () => api.deletePrayer(prayer.id),
    onMutate: async () => {
      await client.cancelQueries({ queryKey: ["prayers"] });
      const previous = client.getQueryData<Prayer[]>(["prayers"]);
      client.setQueryData<Prayer[]>(["prayers"], (items) => items?.filter((p) => p.id !== prayer.id));
      return { previous };
    },
    onError: (_e, _v, ctx) => client.setQueryData(["prayers"], ctx?.previous),
    onSettled: () => client.invalidateQueries({ queryKey: ["prayers"] }),
  });
  const answered = prayer.status === "respondido";
  return (
    <li className={`rounded-lg border p-4 ${answered ? "border-oliva/40 bg-oliva/5" : "border-borda bg-pergaminho-claro"}`}>
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-escritura text-lg font-bold text-couro">{prayer.title}</h3>
        <span className="shrink-0 text-xs text-tinta-suave">
          {answered && prayer.answered_at ? `respondida em ${longDay(prayer.answered_at)}` : `desde ${longDay(prayer.created_at)}`}
        </span>
      </div>
      {prayer.details && <p className="mt-1 whitespace-pre-wrap text-tinta-suave">{prayer.details}</p>}
      {answered && prayer.answer_note && (
        <p className="mt-2 border-l-2 border-oliva pl-3 whitespace-pre-wrap italic">{prayer.answer_note}</p>
      )}
      {answering && (
        <div className="mt-3">
          <label htmlFor={`note-${prayer.id}`} className="text-sm font-bold text-oliva">Como Deus respondeu? (opcional)</label>
          <textarea
            id={`note-${prayer.id}`}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            maxLength={4000}
            className="mt-1 w-full rounded border border-borda bg-pergaminho p-2"
          />
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        {!answered && !answering && (
          <button type="button" onClick={() => setAnswering(true)} className="rounded-full bg-oliva px-3 py-1.5 font-bold text-pergaminho-claro">
            Marcar como respondida
          </button>
        )}
        {answering && (
          <button
            type="button"
            onClick={() => {
              change.mutate({ status: "respondido", answer_note: note.trim() || null });
              setAnswering(false);
            }}
            className="rounded-full bg-oliva px-3 py-1.5 font-bold text-pergaminho-claro"
          >
            Glória a Deus, guardar
          </button>
        )}
        {answered && (
          <button type="button" onClick={() => change.mutate({ status: "aberto", answer_note: prayer.answer_note })} className="rounded-full px-3 py-1.5 hover:bg-borda/60">
            Reabrir
          </button>
        )}
        {!confirming ? (
          <button type="button" onClick={() => setConfirming(true)} className="rounded-full px-3 py-1.5 text-vinho hover:bg-vinho/10">
            Apagar
          </button>
        ) : (
          <span className="flex items-center gap-2">
            <span className="text-vinho">Apagar este pedido?</span>
            <button type="button" onClick={() => remove.mutate()} className="rounded-full bg-vinho px-3 py-1.5 font-bold text-pergaminho-claro">Sim, apagar</button>
            <button type="button" onClick={() => setConfirming(false)} className="rounded-full px-3 py-1.5">Cancelar</button>
          </span>
        )}
        {(change.isError || remove.isError) && <span className="text-vinho">{OFFLINE}</span>}
      </div>
    </li>
  );
}

function Prayers() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["prayers"], queryFn: api.prayers });
  const groups = groupPrayers(data ?? []);
  return (
    <div className="space-y-6">
      <NewPrayer />
      {isLoading && <BlockSkeleton lines={4} />}
      {isError && <p className="text-vinho">{OFFLINE}</p>}
      {data && data.length === 0 && <Empty>Nenhum pedido ainda. Escreva acima pelo que você está orando.</Empty>}
      {groups.open.length > 0 && (
        <section>
          <h2 className="mb-2 font-escritura text-xl font-bold text-couro">Orando</h2>
          <ul className="space-y-3">{groups.open.map((p) => <PrayerCard key={p.id} prayer={p} />)}</ul>
        </section>
      )}
      {groups.answered.length > 0 && (
        <section>
          <h2 className="mb-2 font-escritura text-xl font-bold text-oliva">Respondidas</h2>
          <ul className="space-y-3">{groups.answered.map((p) => <PrayerCard key={p.id} prayer={p} />)}</ul>
        </section>
      )}
    </div>
  );
}

function NoteCard({ note }: { note: VerseNote }) {
  const client = useQueryClient();
  const remove = useMutation({
    mutationFn: () => api.deleteVerseNote(note.id),
    onMutate: async () => {
      await client.cancelQueries({ queryKey: ["verse-notes"] });
      const previous = client.getQueryData<VerseNote[]>(["verse-notes"]);
      client.setQueryData<VerseNote[]>(["verse-notes"], (items) => items?.filter((n) => n.id !== note.id));
      return { previous };
    },
    onError: (_e, _v, ctx) => client.setQueryData(["verse-notes"], ctx?.previous),
    onSettled: () => client.invalidateQueries({ queryKey: ["verse-notes"] }),
  });
  return (
    <li className="rounded-lg border border-borda bg-pergaminho-claro p-4">
      <div className="flex items-baseline justify-between gap-3">
        <RefButton reference={note.reference} />
        <span className="text-xs text-tinta-suave">{longDay(note.updated_at)}</span>
      </div>
      <p className="mt-1 whitespace-pre-wrap">{note.content}</p>
      <button type="button" onClick={() => remove.mutate()} className="mt-2 rounded-full px-3 py-1 text-sm text-vinho hover:bg-vinho/10">
        Apagar anotação
      </button>
    </li>
  );
}

function Notes() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["verse-notes"], queryFn: api.verseNotes });
  if (isLoading) return <BlockSkeleton lines={5} />;
  if (isError) return <p className="text-vinho">{OFFLINE}</p>;
  if (!data?.length)
    return <Empty>Nenhuma anotação ainda. Abra qualquer versículo e escreva em Minha anotação.</Empty>;
  return <ul className="space-y-3">{data.map((n) => <NoteCard key={n.id} note={n} />)}</ul>;
}

export function DiaryPage() {
  const [tab, setTab] = useState<Tab>("palavras");
  return (
    <>
      <p className="mt-2 max-w-[65ch] text-tinta-suave">
        Sua caminhada guardada neste computador: as palavras que você recebeu, as orações e o que Deus respondeu,
        e suas anotações nos versículos.
      </p>
      <div role="tablist" aria-label="Seções do diário" className="mt-6 mb-5 flex flex-wrap gap-1 border-b border-borda">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-bold ${tab === t.id ? "border-ouro text-couro" : "border-transparent text-tinta-suave hover:text-couro"}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "palavras" && <Words />}
      {tab === "oracoes" && <Prayers />}
      {tab === "anotacoes" && <Notes />}
      <VersePopup />
    </>
  );
}
