"use client";

import { useEffect, useRef, useState } from "react";
import { EFFORTS, type EffortId, MODELS, type ModelId } from "@/lib/chatOptions";
import { useChat } from "@/stores/chat";

export const WORD_FOR_ME = "✨ Uma palavra pra mim";

const CONTROL = "inline-flex h-8 items-center rounded-full text-sm transition-colors";
const toggle = (on: boolean) =>
  `${CONTROL} border px-3 ${on ? "border-couro bg-couro text-pergaminho-claro" : "border-borda text-couro hover:border-ouro"}`;

function Chevron() {
  return (
    <svg aria-hidden viewBox="0 0 10 6" className="pointer-events-none absolute right-2.5 h-1.5 w-2.5 text-tinta-suave">
      <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function Choice<T extends string>({
  id,
  label,
  value,
  items,
  onChange,
}: {
  id: string;
  label: string;
  value: T;
  items: readonly { id: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <span className="relative inline-flex items-center">
      <label htmlFor={id} className="sr-only">{label}</label>
      <select
        id={id}
        value={value}
        title={label}
        onChange={(e) => onChange(e.target.value as T)}
        className="h-8 cursor-pointer appearance-none rounded-full bg-transparent pr-6 pl-2.5 text-sm text-couro [field-sizing:content] hover:bg-ouro-claro/40 focus-visible:outline-2 focus-visible:outline-ouro"
      >
        {items.map((item) => (
          <option key={item.id} value={item.id}>{item.label}</option>
        ))}
      </select>
      <Chevron />
    </span>
  );
}

export function Composer({ onSent }: { onSent?: () => void }) {
  const [text, setText] = useState("");
  const streaming = useChat((s) => s.streaming);
  const send = useChat((s) => s.send);
  const loadDailyWord = useChat((s) => s.loadDailyWord);
  const dailyLoading = useChat((s) => s.daily.status === "loading");
  const options = useChat((s) => s.options);
  const setOptions = useChat((s) => s.setOptions);
  const restoreOptions = useChat((s) => s.restoreOptions);
  const studyPlan = useChat((s) => s.studyPlan);
  const setStudyPlan = useChat((s) => s.setStudyPlan);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(restoreOptions, [restoreOptions]);

  const submit = async (value: string) => {
    if (!value.trim() || streaming) return;
    setText("");
    await send(value.trim());
    onSent?.();
  };

  return (
    <form
      className="mx-auto w-full max-w-3xl px-5 pb-3"
      onSubmit={(e) => {
        e.preventDefault();
        void submit(text);
      }}
    >
      <div className="rounded-2xl border border-borda bg-pergaminho-claro shadow-[0_1px_0_#dccfb0,0_18px_40px_-30px_rgba(74,53,36,0.6)] transition-colors focus-within:border-ouro">
        <label htmlFor="mensagem" className="sr-only">Mensagem</label>
        <textarea
          id="mensagem"
          ref={input}
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
          placeholder={
            studyPlan
              ? "Qual tema você quer estudar? Ex.: a aliança de Deus com Abraão"
              : "Escreva o que está no seu coração..."
          }
          className="block w-full resize-none bg-transparent px-4 pt-3.5 pb-1 text-[1.0625rem] leading-relaxed placeholder:text-tinta-suave/70 focus:outline-none focus-visible:outline-none"
        />
        <div className="@container flex flex-wrap items-center gap-1.5 px-2.5 pb-2.5">
          <button
            type="button"
            disabled={dailyLoading}
            onClick={() => {
              void loadDailyWord();
              onSent?.();
            }}
            className={`${CONTROL} order-1 px-2.5 font-bold @min-[44rem]:order-none text-couro hover:bg-ouro-claro/60 disabled:opacity-50`}
          >
            {WORD_FOR_ME}
          </button>
          <button
            type="button"
            aria-pressed={studyPlan}
            onClick={() => {
              setStudyPlan(!studyPlan);
              input.current?.focus();
            }}
            title="Escreva um tema e receba um plano de estudo em tópicos"
            className={`${toggle(studyPlan)} order-3 @min-[44rem]:order-none`}
          >
            <span className="@min-[44rem]:hidden">Plano</span>
            <span className="hidden @min-[44rem]:inline">Plano de estudo</span>
          </button>
          <button
            type="button"
            aria-pressed={options.brief}
            onClick={() => setOptions({ brief: !options.brief })}
            title="Só o essencial, sem precisar pedir"
            className={`${toggle(options.brief)} order-3 @min-[44rem]:order-none @min-[44rem]:ml-auto`}
          >
            <span className="@min-[44rem]:hidden">Curta</span>
            <span className="hidden @min-[44rem]:inline">Resposta curta</span>
          </button>
          <div className={`${CONTROL} order-3 border border-borda hover:border-ouro @min-[44rem]:order-none`}>
            <Choice
              id="modelo"
              label="Modelo"
              value={options.model}
              items={MODELS}
              onChange={(model: ModelId) => setOptions({ model })}
            />
            <span aria-hidden className="h-4 w-px bg-borda" />
            <Choice
              id="esforco"
              label="Esforço de raciocínio"
              value={options.effort}
              items={EFFORTS}
              onChange={(effort: EffortId) => setOptions({ effort })}
            />
          </div>
          <button
            type="submit"
            disabled={streaming || !text.trim()}
            className={`${CONTROL} order-2 ml-auto bg-couro px-5 font-bold text-pergaminho-claro hover:bg-couro-claro disabled:opacity-40 @min-[44rem]:order-none @min-[44rem]:ml-0`}
          >
            Enviar
          </button>
          <span aria-hidden className="order-2 basis-full @min-[44rem]:hidden" />
        </div>
      </div>
      <p className="mt-2 text-center text-xs text-tinta-suave">
        Todo versículo vem do texto bíblico e passa por conferência automática. Você pode clicar na referência.
      </p>
    </form>
  );
}
