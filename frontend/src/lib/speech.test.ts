import { afterEach, describe, expect, test, vi } from "vitest";
import { pickVoice, speak, verseUtterance } from "./speech";

const voice = (lang: string, name = lang) => ({ lang, name }) as SpeechSynthesisVoice;

describe("speech", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("prefers a pt-BR voice, then any Portuguese voice", () => {
    expect(pickVoice([voice("en-US"), voice("pt-PT"), voice("pt-BR")])?.lang).toBe("pt-BR");
    expect(pickVoice([voice("en-US"), voice("pt-PT")])?.lang).toBe("pt-PT");
    expect(pickVoice([voice("en-US")])).toBeNull();
  });

  test("utterance announces the reference before the text", () => {
    expect(verseUtterance("Gálatas", 6, [{ n: 9, text: "Não desanimemos." }])).toBe(
      "Gálatas, capítulo 6, versículo 9. Não desanimemos.",
    );
    expect(verseUtterance("Salmos", 23, [{ n: 1, text: "A." }, { n: 2, text: "B." }])).toBe(
      "Salmos, capítulo 23, versículos 1 a 2. A. B.",
    );
  });

  test("speak cancels what is playing and uses Portuguese", () => {
    const calls: string[] = [];
    let spoken: { lang: string; voice: SpeechSynthesisVoice | null; text: string } | null = null;
    vi.stubGlobal("SpeechSynthesisUtterance", class {
      lang = "";
      voice: SpeechSynthesisVoice | null = null;
      rate = 1;
      onend: (() => void) | null = null;
      constructor(public text: string) {}
    });
    vi.stubGlobal("speechSynthesis", {
      getVoices: () => [voice("pt-BR")],
      cancel: () => calls.push("cancel"),
      speak: (u: { lang: string; voice: SpeechSynthesisVoice | null; text: string }) => {
        calls.push("speak");
        spoken = u;
      },
    });
    speak("Olá");
    expect(calls).toEqual(["cancel", "speak"]);
    expect(spoken).toMatchObject({ lang: "pt-BR", text: "Olá" });
  });
});
