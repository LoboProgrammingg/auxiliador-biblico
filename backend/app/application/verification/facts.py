"""Conferência de fatos em volta do texto: parentescos e ocorrências de palavras do original.

O Jev classifica o que a frase afirma; o banco (TIPNR e STEPBible) diz se confere. Sem Jev, expressões simples
fazem a classificação. Só se aponta erro quando a base conhece a resposta certa.
"""

import re
from typing import Any

from app.application.judgments.service import FactClaim, JudgmentService
from app.domain.bible.books import BOOKS
from app.domain.bible.repositories import BibleRepository

MAX_SENTENCES = 6
MAX_DEPTH = 4
_SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")
_NAME = re.compile(r"\b[A-ZÁÂÃÉÊÍÓÔÕÚÇ][a-záâãéêíóôõúç]{2,}\b")
_STRONG = re.compile(r"\b([HG]\d{1,5}[A-Za-z]?)\b")
_KINSHIP = re.compile(
    r"\b(pai|m[ãa]e|av[ôóo]|bisav[ôóo]|filh[oa]|net[oa]|bisnet[oa]|esposa|marido|cas(?:ou|aram|ado|ada))\b", re.I
)
_COUNT = re.compile(r"(só aparece|aparece apenas|única vez|uma vez só|apenas uma vez|\d+\s+vezes|aparece em \d+)", re.I)
_NUMBER = re.compile(r"(\d+)\s+(?:vezes|versículos|lugares)")
RELATION_WORDS = [
    (re.compile(r"\bbisav[ôóo]", re.I), "bisavo"),
    (re.compile(r"\bbisnet[oa]", re.I), "bisneto"),
    (re.compile(r"\bav[ôóo]\b", re.I), "avo"),
    (re.compile(r"\bnet[oa]\b", re.I), "neto"),
    (re.compile(r"\b(pai|m[ãa]e)\b", re.I), "pai_ou_mae"),
    (re.compile(r"\bfilh[oa]\b", re.I), "filho"),
    (re.compile(r"\b(esposa|marido|cas(?:ou|aram|ado|ada))\b", re.I), "conjuge"),
]
UP = {"pai_ou_mae": 1, "avo": 2, "bisavo": 3}
DOWN = {"filho": 1, "neto": 2, "bisneto": 3}


def candidate_sentences(prose: str) -> list[str]:
    found = []
    for raw in _SENTENCE.findall(prose):
        sentence = raw.strip()
        kinship = _KINSHIP.search(sentence) and len(set(_NAME.findall(sentence))) >= 2
        count = _STRONG.search(sentence) and _COUNT.search(sentence)
        if kinship or count:
            found.append(sentence)
    return found[:MAX_SENTENCES]


def _fallback(sentence: str) -> FactClaim:
    if _STRONG.search(sentence) and _COUNT.search(sentence):
        unique = re.search(r"só aparece|única vez|uma vez só|apenas uma vez|aparece apenas", sentence, re.I)
        return FactClaim("ocorrencias", None, "unica" if unique else "numero")
    relation = next((rel for pattern, rel in RELATION_WORDS if pattern.search(sentence)), None)
    return FactClaim("parentesco", relation, None) if relation else FactClaim("outra", None, None)


async def _parents(repo: BibleRepository, ids: set[str]) -> dict[str, list[str]]:
    parents: dict[str, list[str]] = {}
    for rel in await repo.relations(sorted(ids)):
        if rel.kind == "pai_mae":
            parents.setdefault(rel.person_id, []).append(rel.other_id)
    return parents


async def _lineage(repo: BibleRepository, start: str) -> dict[str, list[str]]:
    """Ancestrais de `start` até MAX_DEPTH gerações, cada um com o caminho até ele (start primeiro)."""
    paths = {start: [start]}
    frontier = {start}
    for _ in range(MAX_DEPTH):
        parents = await _parents(repo, frontier)
        frontier = set()
        for child, ps in parents.items():
            for parent in ps:
                if parent not in paths:
                    paths[parent] = [*paths[child], parent]
                    frontier.add(parent)
        if not frontier:
            break
    return paths


async def _kinship_issue(
    repo: BibleRepository, sentence: str, relation: str, a_name: str, b_name: str, people: list[tuple[str, str]]
) -> dict[str, Any] | None:
    names = {pid: name for pid, name in people}
    a_ids = [pid for pid, n in people if n.split(" (")[0] == a_name]
    b_ids = [pid for pid, n in people if n.split(" (")[0] == b_name]
    known: list[list[str]] = []
    for a in a_ids:
        for b in b_ids:
            if relation == "conjuge":
                spouses = {r.other_id for r in await repo.relations([a]) if r.kind == "conjuge"}
                spouses |= {r.person_id for r in await repo.relations([b]) if r.kind == "conjuge" and r.other_id == a}
                if b in spouses:
                    return None
                continue
            up, down = await _lineage(repo, b), await _lineage(repo, a)
            if a in up:
                path = list(reversed(up[a]))
                if UP.get(relation) == len(path) - 1:
                    return None
                known.append(path)
            if b in down:
                path = down[b]
                if DOWN.get(relation) == len(path) - 1:
                    return None
                known.append(list(reversed(path)))
    if not known:
        return None
    path = min(known, key=len)
    names |= await repo.person_names([pid for pid in path if pid not in names])
    chain = " → ".join(names.get(pid, pid).split(" (")[0] for pid in path)
    return {
        "kind": "fato_nao_confere",
        "excerpt": sentence[:200],
        "correction": f"Pela base de famílias (STEPBible): {chain}.",
    }


async def _occurrence_issue(repo: BibleRepository, sentence: str, claim: str) -> dict[str, Any] | None:
    match = _STRONG.search(sentence)
    if match is None:
        return None
    strong = match.group(1)
    total, verses, books = await repo.strong_stats(strong)
    if total == 0:
        return None
    number = _NUMBER.search(sentence)
    if claim == "unica" and verses <= 1:
        return None
    if claim == "numero" and (number is None or int(number.group(1)) in (total, verses)):
        return None
    names = ", ".join(BOOKS[b - 1].pt_name for b in books[:5]) + (" e outros" if len(books) > 5 else "")
    where = f"{verses} versículos" if verses > 1 else "1 versículo"
    return {
        "kind": "fato_nao_confere",
        "excerpt": sentence[:200],
        "correction": f"No texto original, {strong} aparece em {where} ({names}).",
    }


async def check_facts(prose: str, repo: BibleRepository, judgments: JudgmentService) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for sentence in candidate_sentences(prose):
        tokens = list(dict.fromkeys(_NAME.findall(sentence)))
        people = await repo.people_named(tokens) if tokens else []
        present = {n.split(" (")[0] for _, n in people}
        ordered = [t for t in tokens if t in present]
        a_name, b_name = (ordered + [None, None])[:2]
        claim = await judgments.classify_fact(sentence, a_name, b_name) or _fallback(sentence)
        issue = None
        if claim.kind == "parentesco" and claim.relation and claim.relation != "nenhum" and a_name and b_name:
            issue = await _kinship_issue(repo, sentence, claim.relation, a_name, b_name, people)
        elif claim.kind == "ocorrencias" and claim.occurrences in ("unica", "numero"):
            issue = await _occurrence_issue(repo, sentence, claim.occurrences)
        if issue is not None:
            issues.append(issue)
    return issues
