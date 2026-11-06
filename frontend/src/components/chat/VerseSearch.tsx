"use client";

import { useState } from "react";
import { api } from "@/services/api";
import { useChat } from "@/stores/chat";

export const VERSE_SEARCH_ID = "ir-versiculo";

/** Abre direto a gaveta de uma passagem (ex.: Jo 3:16, Salmos 23); referência que não existe não abre nada. */
export function VerseSearch() {
  const openPopup = useChat((s) => s.openPopup);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const go = async () => {
    const ref = value.trim();
    if (ref.length < 2) return;
    setBusy(true);
    setError(null);
    try {
      const passage = await api.passage(ref, "vfl", 0);
      openPopup({ reference: passage.reference, translation: "vfl" });
      setValue("");
    } catch {
      setError("Não encontrei essa referência.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <form
      className="px-3 pb-2"
      onSubmit={(e) => {
        e.preventDefault();
        void go();
      }}
    >
      <label htmlFor={VERSE_SEARCH_ID} className="sr-only">Ir para versículo</label>
      <input
        id={VERSE_SEARCH_ID}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        maxLength={60}
        placeholder="Ir para versículo (Ctrl+J)"
        disabled={busy}
        className="w-full rounded-lg border border-pergaminho-claro/20 bg-couro-claro/40 px-3 py-1.5 text-sm text-pergaminho-claro placeholder:text-pergaminho-claro/60 focus:border-ouro-claro focus:outline-none"
      />
      {error && <p role="status" className="mt-1 text-xs text-ouro-claro">{error}</p>}
    </form>
  );
}
