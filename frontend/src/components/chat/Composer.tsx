"use client";

import { useEffect, useState } from "react";
import { EFFORTS, type EffortId, MODELS, type ModelId } from "@/lib/chatOptions";
import { useChat } from "@/stores/chat";

export const WORD_FOR_ME = "✨ Uma palavra pra mim";
const SELECT =
  "rounded-full border border-borda bg-pergaminho-claro px-2.5 py-1 text-sm text-couro hover:border-ouro focus:border-ouro focus:outline-none";

export function Composer({ onSent }: { onSent?: () => void }) {
  const [text, setText] = useState("");
  const streaming = useChat((s) => s.streaming);
  const send = useChat((s) => s.send);
  const loadDailyWord = useChat((s) => s.loadDailyWord);
  const dailyLoading = useChat((s) => s.daily.status === "loading");
  const options = useChat((s) => s.options);
  const setOptions = useChat((s) => s.setOptions);
  const restoreOptions = useChat((s) => s.restoreOptions);

  useEffect(restoreOptions, [restoreOptions]);

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
      <div className="rounded-2xl border border-borda bg-pergaminho-claro shadow-[0_1px_0_#dccfb0,0_18px_40px_-30px_rgba(74,53,36,0.6)] transition-colors focus-within:border-ouro">
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
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 pb-2.5">
          <button
            type="button"
            disabled={dailyLoading}
            onClick={() => {
              void loadDailyWord();
              onSent?.();
            }}
            className="rounded-full px-3 py-1.5 text-sm font-bold text-couro hover:bg-ouro-claro/60 disabled:opacity-50"
          >
            {WORD_FOR_ME}
          </button>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              aria-pressed={options.brief}
              onClick={() => setOptions({ brief: !options.brief })}
              title="Respostas curtas, só o essencial"
              className={`rounded-full border px-3 py-1 text-sm font-bold transition-colors ${
                options.brief
                  ? "border-couro bg-couro text-pergaminho-claro"
                  : "border-borda text-couro hover:border-ouro"
              }`}
            >
              Resposta curta
            </button>
            <label className="sr-only" htmlFor="modelo">Modelo</label>
            <select
              id="modelo"
              value={options.model}
              onChange={(e) => setOptions({ model: e.target.value as ModelId })}
              className={SELECT}
            >
              {MODELS.map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
            <label className="sr-only" htmlFor="esforco">Esforço</label>
            <select
              id="esforco"
              value={options.effort}
              onChange={(e) => setOptions({ effort: e.target.value as EffortId })}
              className={SELECT}
              title="Esforço de raciocínio"
            >
              {EFFORTS.map((ef) => (
                <option key={ef.id} value={ef.id}>{ef.label}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={streaming || !text.trim()}
              className="rounded-full bg-couro px-5 py-1.5 text-sm font-bold text-pergaminho-claro hover:bg-couro-claro disabled:opacity-40"
            >
              Enviar
            </button>
          </div>
        </div>
      </div>
      <p className="mt-1.5 text-center text-xs text-tinta-suave">
        Todo versículo vem do texto bíblico e passa por conferência automática. Você pode clicar na referência.
      </p>
    </form>
  );
}
