"use client";

import { useState } from "react";
import { useChat } from "@/stores/chat";

export const WORD_FOR_ME = "✨ Uma palavra pra mim";

export function Composer({ onSent }: { onSent?: () => void }) {
  const [text, setText] = useState("");
  const streaming = useChat((s) => s.streaming);
  const send = useChat((s) => s.send);

  const submit = async (value: string) => {
    if (!value.trim() || streaming) return;
    setText("");
    await send(value.trim());
    onSent?.();
  };

  return (
    <form
      className="mx-auto w-full max-w-3xl px-4 pb-4"
      onSubmit={(e) => {
        e.preventDefault();
        void submit(text);
      }}
    >
      <div className="rounded-2xl border border-borda bg-pergaminho-claro shadow-[0_1px_0_#dccfb0] focus-within:border-ouro">
        <label htmlFor="mensagem" className="sr-only">Mensagem</label>
        <textarea
          id="mensagem"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit(text);
            }
          }}
          rows={2}
          maxLength={8000}
          placeholder="Escreva o que está no seu coração..."
          className="block w-full resize-none bg-transparent px-4 pt-3 text-[1.0625rem] leading-relaxed placeholder:text-tinta-suave/70 focus:outline-none focus-visible:outline-none"
        />
        <div className="flex items-center justify-between gap-2 px-3 pb-2.5">
          <button
            type="button"
            disabled={streaming}
            onClick={() => void submit(WORD_FOR_ME)}
            className="rounded-full px-3 py-1.5 text-sm font-bold text-couro hover:bg-ouro-claro/60 disabled:opacity-50"
          >
            {WORD_FOR_ME}
          </button>
          <button
            type="submit"
            disabled={streaming || !text.trim()}
            className="rounded-full bg-couro px-5 py-1.5 text-sm font-bold text-pergaminho-claro hover:bg-couro-claro disabled:opacity-40"
          >
            Enviar
          </button>
        </div>
      </div>
      <p className="mt-1.5 text-center text-xs text-tinta-suave">
        Todo versículo vem do texto bíblico e passa por conferência automática. Você pode clicar na referência.
      </p>
    </form>
  );
}
