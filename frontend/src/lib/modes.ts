import type { EffortId } from "./chatOptions";

/** Botões de uma mensagem só; podem ficar ligados juntos. */
export interface Modes {
  plan: boolean;
  video: boolean;
  complex: boolean;
}

export const NO_MODES: Modes = { plan: false, video: false, complex: false };

export function requestModes(modes: Modes): Modes {
  return { plan: modes.plan, video: modes.video, complex: modes.complex };
}

const RANK: Record<EffortId, number> = { medium: 0, high: 1, xhigh: 2 };

/** Complexo pede o esforço extra alto e o vídeo, o alto; uma escolha maior da pessoa nunca é rebaixada. */
export function effortFor(chosen: EffortId, modes: Modes): EffortId {
  const minimum: EffortId = modes.complex ? "xhigh" : modes.video ? "high" : "medium";
  return RANK[minimum] > RANK[chosen] ? minimum : chosen;
}

export function placeholderFor(modes: Modes): string {
  if (modes.video) return "Sobre o que é o vídeo? Ex.: os querubins como a Bíblia descreve (ou deixe que eu escolha)";
  if (modes.complex) return "O que você quer destrinchar por completo? Ex.: por que Deus endureceu o coração de Faraó";
  if (modes.plan) return "Qual tema você quer estudar? Ex.: a aliança de Deus com Abraão";
  return "Escreva o que está no seu coração...";
}
