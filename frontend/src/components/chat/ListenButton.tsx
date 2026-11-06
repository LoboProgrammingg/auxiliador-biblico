"use client";

import { useState, useSyncExternalStore } from "react";
import { canSpeak, speak, stopSpeaking, verseUtterance } from "@/lib/speech";
import type { VerseText } from "@/types/api";

const noop = () => () => {};

export function ListenButton({ book, chapter, verses }: { book: string; chapter: number; verses: VerseText[] }) {
  const supported = useSyncExternalStore(noop, canSpeak, () => false);
  const [playing, setPlaying] = useState(false);
  if (!supported || verses.length === 0) return null;
  const toggle = () => {
    if (playing) {
      stopSpeaking();
      setPlaying(false);
      return;
    }
    setPlaying(true);
    speak(verseUtterance(book, chapter, verses), () => setPlaying(false));
  };
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={playing}
      aria-label={playing ? "Parar a leitura" : `Ouvir ${book} ${chapter}`}
      className="rounded-full px-2 py-0.5 text-sm text-couro hover:bg-ouro-claro/50"
    >
      {playing ? "■ Parar" : "🔊 Ouvir"}
    </button>
  );
}
