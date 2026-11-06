import logging
import re
from dataclasses import dataclass
from typing import Any

from app.application.judgments.ports import Judge, JudgeAnswers, JudgeUnavailable, Question
from app.application.judgments.questions import FACT, FIDELITY, GUARD, GUARD_KINDS, SENSITIVE, TRIAGE

logger = logging.getLogger(__name__)
CRISIS_THRESHOLD = 0.5
GUARD_THRESHOLD = 0.7
FIDELITY_CONFIDENCE = 0.8
SENSITIVE_THRESHOLD = 0.7
FACT_CONFIDENCE = 0.7
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_SENTENCE = re.compile(r"^\s*([^\s,;:].*?[.!?])(?:\s|$)", re.S)


@dataclass(frozen=True)
class Triage:
    crisis: float
    moment: str
    moment_confidence: float
    distress: float


@dataclass(frozen=True)
class FactClaim:
    kind: str
    relation: str | None
    occurrences: str | None


@dataclass(frozen=True)
class FidelityIssue:
    marker: str
    claim: str
    confidence: float


def triage_block(t: Triage) -> str:
    risk = "alto" if t.crisis >= CRISIS_THRESHOLD else "baixo"
    return f"[Triagem automática: momento={t.moment}; angústia={t.distress:.1f}/3; risco_à_vida={risk}]"


def sentence_after(text: str) -> str:
    match = _SENTENCE.match(text.lstrip("\n"))
    sentence = match.group(1).strip() if match else ""
    return sentence if 20 <= len(sentence) <= 300 else ""


class JudgmentService:
    def __init__(self, judge: Judge | None) -> None:
        self._judge = judge

    async def _ask(self, state: dict[str, Any], questions: dict[str, Question]) -> JudgeAnswers | None:
        if self._judge is None:
            return None
        try:
            return await self._judge.ask(state, questions)
        except JudgeUnavailable as exc:
            logger.warning("Jev indisponível: %s", exc)
            return None

    async def triage(self, user_text: str) -> Triage | None:
        answers = await self._ask({"mensagem": user_text}, dict(TRIAGE))
        if answers is None:
            return None
        moment, confidence = answers.choices.get("momento", ("outro", 0.0))
        return Triage(
            answers.nouls.get("crise", 0.0), moment, confidence, answers.scores.get("angustia", (0.0, 0.0))[0]
        )

    async def guard_issues(self, answer_text: str) -> list[dict[str, str]]:
        answers = await self._ask({"resposta": answer_text[:20000]}, dict(GUARD))
        if answers is None:
            return []
        return [
            {"kind": GUARD_KINDS[key], "excerpt": f"probabilidade {answers.nouls[key]:.2f}"}
            for key in GUARD
            if answers.nouls.get(key, 0.0) >= GUARD_THRESHOLD
        ]

    async def fidelity(self, pairs: list[tuple[str, str, str]]) -> list[FidelityIssue]:
        issues: list[FidelityIssue] = []
        for marker, verse_text, claim in pairs:
            if not claim:
                continue
            answers = await self._ask({"versiculo": verse_text, "afirmacao": claim}, dict(FIDELITY))
            if answers is None:
                return issues
            choice, confidence = answers.choices.get("relacao", ("apoia", 0.0))
            if choice == "contradiz" and confidence >= FIDELITY_CONFIDENCE:
                issues.append(FidelityIssue(marker, claim, confidence))
        return issues

    async def contains_sensitive_data(self, content: str) -> bool:
        if _CPF.search(content) or _CARD.search(content):
            return True
        answers = await self._ask({"conteudo": content}, dict(SENSITIVE))
        return answers is not None and answers.nouls.get("sensivel", 0.0) >= SENSITIVE_THRESHOLD

    async def classify_fact(self, sentence: str, person_a: str | None, person_b: str | None) -> FactClaim | None:
        """Jev diz que tipo de fato a frase afirma; None = Jev indisponível (quem chama usa o plano B)."""
        state = {"frase": sentence, "pessoa_a": person_a or "", "pessoa_b": person_b or ""}
        answers = await self._ask(state, dict(FACT))
        if answers is None:
            return None
        kind, confidence = answers.choices.get("tipo", ("outra", 0.0))
        if confidence < FACT_CONFIDENCE or kind == "outra":
            return FactClaim("outra", None, None)
        relation, rel_conf = answers.choices.get("parentesco", ("nenhum", 0.0))
        occurrences, occ_conf = answers.choices.get("ocorrencias", ("nao_afirma", 0.0))
        return FactClaim(
            kind,
            relation if rel_conf >= FACT_CONFIDENCE else None,
            occurrences if occ_conf >= FACT_CONFIDENCE else None,
        )
