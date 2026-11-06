/** Leitura em voz alta pelo próprio navegador (Web Speech API): sem serviço externo, sem custo. */

export function canSpeak(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

export function pickVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const lower = (v: SpeechSynthesisVoice) => v.lang.toLowerCase().replace("_", "-");
  return voices.find((v) => lower(v) === "pt-br") ?? voices.find((v) => lower(v).startsWith("pt")) ?? null;
}

export function verseUtterance(book: string, chapter: number, verses: { n: number; text: string }[]): string {
  const first = verses[0]?.n;
  const last = verses[verses.length - 1]?.n;
  const which = first === last ? `versículo ${first}` : `versículos ${first} a ${last}`;
  return `${book}, capítulo ${chapter}, ${which}. ${verses.map((v) => v.text).join(" ")}`;
}

export function speak(text: string, onEnd?: () => void): void {
  const synth = globalThis.speechSynthesis;
  synth.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "pt-BR";
  utterance.voice = pickVoice(synth.getVoices());
  utterance.rate = 0.95;
  utterance.onend = () => onEnd?.();
  synth.speak(utterance);
}

export function stopSpeaking(): void {
  globalThis.speechSynthesis?.cancel();
}
