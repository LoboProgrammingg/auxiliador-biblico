"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { useChat, type PopupTarget } from "@/stores/chat";
import { ListenButton } from "./ListenButton";
import { BlockSkeleton } from "./Skeletons";

const TABS = ["vfl", "acf", "nvt"] as const;

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-borda py-4">
      <h3 className="mb-2 font-escritura text-base font-bold text-couro">{title}</h3>
      {children}
    </section>
  );
}

function Context({ reference, translation }: { reference: string; translation: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["passage", reference, translation],
    queryFn: () => api.passage(reference, translation, 3),
  });
  if (isLoading) return <BlockSkeleton lines={5} />;
  if (isError || !data) return <p className="text-sm text-vinho">Não consegui carregar esta passagem.</p>;
  return (
    <div className="font-escritura text-[1.05rem] leading-[1.75]">
      {data.verses.map((v) => (
        <p key={v.n} className={v.cited ? "rounded bg-ouro-claro/50 px-1" : "px-1 text-tinta-suave"}>
          <sup className="mr-1 text-xs font-bold text-ouro">{v.n}</sup>
          {v.text}
        </p>
      ))}
      {data.fallback_label && <p className="mt-2 text-xs italic text-tinta-suave">{data.fallback_label}</p>}
      <div className="mt-2">
        <ListenButton book={data.book} chapter={data.chapter} verses={data.verses.filter((v) => v.cited)} />
      </div>
    </div>
  );
}

function Original({ reference }: { reference: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["original", reference], queryFn: () => api.original(reference) });
  if (isLoading) return <BlockSkeleton lines={4} />;
  if (!data?.words.length) return <p className="text-sm text-tinta-suave">Sem texto original para este trecho.</p>;
  const rtl = data.words[0].language !== "grc";
  return (
    <ul className="grid grid-cols-[repeat(auto-fill,minmax(8.5rem,1fr))] gap-2" dir={rtl ? "rtl" : "ltr"}>
      {data.words.map((w, i) => (
        <li key={`${w.verse}-${w.position}-${i}`} className="rounded border border-borda bg-pergaminho-claro p-2" dir="ltr">
          <p className={`text-xl ${w.language === "grc" ? "font-escritura" : "font-hebraico"}`} dir={rtl ? "rtl" : "ltr"}>
            {w.surface.replaceAll("/", "")}
          </p>
          <p className="text-sm italic text-tinta-suave">{w.transliteration.replaceAll("/", "")}</p>
          <p className="text-xs"><span className="font-bold">{w.strong}</span> {w.language === "arc" ? "aramaico" : ""}</p>
          <p className="text-xs text-tinta-suave">{w.lexicon_gloss ?? w.gloss_en} (inglês)</p>
        </li>
      ))}
    </ul>
  );
}

function CrossReferences({ reference }: { reference: string }) {
  const openPopup = useChat((s) => s.openPopup);
  const { data, isLoading } = useQuery({
    queryKey: ["xref", reference],
    queryFn: () => api.crossReferences(reference),
  });
  if (isLoading) return <BlockSkeleton lines={3} />;
  if (!data?.items.length) return <p className="text-sm text-tinta-suave">Nenhuma passagem ligada.</p>;
  return (
    <ul className="flex flex-wrap gap-2">
      {data.items.map((x) => (
        <li key={x.reference}>
          <button
            type="button"
            onClick={() => openPopup({ reference: x.reference, translation: "vfl" })}
            className="rounded-full border border-borda px-3 py-1 text-sm hover:border-ouro hover:bg-ouro-claro/40"
          >
            {x.reference}
          </button>
        </li>
      ))}
    </ul>
  );
}

function MyNote({ reference }: { reference: string }) {
  const client = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["verse-note", reference], queryFn: () => api.verseNote(reference) });
  const [draft, setDraft] = useState<string | null>(null);
  const text = draft ?? data?.content ?? "";
  const save = useMutation({
    mutationFn: () => api.saveVerseNote(reference, text.trim()),
    onSuccess: (note) => {
      client.setQueryData(["verse-note", reference], note);
      setDraft(null);
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["verse-notes"] }),
  });
  const remove = useMutation({
    mutationFn: () => (data ? api.deleteVerseNote(data.id) : Promise.resolve()),
    onSuccess: () => {
      client.setQueryData(["verse-note", reference], null);
      setDraft(null);
    },
    onSettled: () => client.invalidateQueries({ queryKey: ["verse-notes"] }),
  });
  if (isLoading) return <BlockSkeleton lines={2} />;
  return (
    <div>
      <label htmlFor="my-note" className="sr-only">Minha anotação sobre {reference}</label>
      <textarea
        id="my-note"
        value={text}
        onChange={(e) => setDraft(e.target.value)}
        rows={3}
        maxLength={8000}
        placeholder="O que Deus está falando com você por este texto?"
        className="w-full rounded border border-borda bg-pergaminho-claro p-2 leading-relaxed"
      />
      <div className="mt-1 flex items-center gap-2 text-sm">
        <button
          type="button"
          disabled={!text.trim() || text === (data?.content ?? "") || save.isPending}
          onClick={() => save.mutate()}
          className="rounded-full bg-couro px-3 py-1 font-bold text-pergaminho-claro disabled:opacity-40"
        >
          {save.isPending ? "Salvando…" : "Salvar anotação"}
        </button>
        {data && (
          <button type="button" onClick={() => remove.mutate()} className="rounded-full px-3 py-1 text-vinho hover:bg-vinho/10">
            Apagar
          </button>
        )}
        {save.isSuccess && draft === null && <span className="text-oliva">Guardada no Diário.</span>}
        {(save.isError || remove.isError) && <span className="text-vinho">Não consegui salvar.</span>}
      </div>
    </div>
  );
}

export function VersePopup() {
  const popup = useChat((s) => s.popup);
  const close = useChat((s) => s.openPopup);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  if (!popup) return null;
  return <PopupBody key={`${popup.reference}|${popup.translation}`} popup={popup} close={() => close(null)} />;
}

function PopupBody({ popup, close }: { popup: PopupTarget; close: () => void }) {
  const initial = TABS.includes(popup.translation as (typeof TABS)[number]) ? popup.translation : "vfl";
  const [tab, setTab] = useState<string>(initial);
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-tinta/30" onClick={close}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Passagem ${popup.reference}`}
        className="h-full w-full max-w-xl overflow-y-auto bg-pergaminho px-6 py-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="font-escritura text-2xl font-bold text-couro">{popup.reference}</h2>
          <button type="button" onClick={close} className="rounded px-2 py-1 text-sm hover:bg-borda/60">
            Fechar
          </button>
        </div>
        <div role="tablist" className="mt-3 mb-3 flex gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={`rounded-full px-3 py-1 text-sm font-bold ${tab === t ? "bg-couro text-pergaminho-claro" : "text-couro hover:bg-borda/60"}`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>
        <Context reference={popup.reference} translation={tab} />
        <Section title="Minha anotação">
          <MyNote reference={popup.reference} />
        </Section>
        <Section title="Original">
          <Original reference={popup.reference} />
        </Section>
        <Section title="Passagens ligadas">
          <CrossReferences reference={popup.reference} />
        </Section>
      </aside>
    </div>
  );
}
