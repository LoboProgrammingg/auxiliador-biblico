import re
import unicodedata

_STUDY_VERB = re.compile(r"\b(?:interpret\w*|estud\w*|expli[cq]\w*|entender)\b")
_OPINION = re.compile(
    r"\b(?:na sua (?:opiniao|visao)|(?:qual|e) (?:e )?(?:a )?sua (?:opiniao|visao|interpretacao|leitura)"
    r"|o que (?:voce|vc|tu) (?:acha|pensa|entende)|(?:voce|vc) acredita)\b"
)
_BRIEF = re.compile(
    r"\bbrevemente\b|(?<!\bem )\bbreve\b|\bresum\w*|\bsucint\w*|\bem poucas palavras\b"
    r"|\b(?:bem|mais|seja|resposta|texto) curt[oa]\b|\bcurtinh[oa]\b|\bdireto ao ponto\b"
)
_COMPLEX = re.compile(r"^\s*complex[oa]\b")
_THINKERS = re.compile(
    r"filosof\w*|pensador\w*|\bcetic\w*|\bateu\b|\bateus\b|\bateis\w*|agnostic\w*|problema do mal"
    r"|existe (?:o )?mal\b|deus (?:e )?bom|existencia de deus|deus (?:nao )?existe|fe e razao|ciencia e fe"
    r"|sentido da vida|nietzsche|dawkins|darwin|\bhume\b|epicuro|\bsartre\b|\bcamus\b|\bfreud\b|\bmarx\b"
)
_PLAN = re.compile(r"\b(?:plano|roteiro) de estudos?\b")
_WHOLE_CHAPTER = re.compile(r"\bcapitulo\s+\d{1,3}\b|\b[a-z]{2,}\s+\d{1,3}\b(?!\s*[:.,]\s*\d)")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def asks_opinion(text: str) -> bool:
    """A pessoa quer a opinião e a interpretação do próprio auxiliador (na sua opinião, o que você acha…)."""
    return _OPINION.search(_normalize(text)) is not None


def wants_brief(text: str) -> bool:
    """A pessoa pediu resposta curta (breve, brevemente, resumo, em poucas palavras…); em breve não conta."""
    return _BRIEF.search(_normalize(text)) is not None


def wants_plan(text: str) -> bool:
    """A pessoa quer um plano de estudo sobre um tema (plano de leitura não conta)."""
    return _PLAN.search(_normalize(text)) is not None


def wants_thinkers(text: str) -> bool:
    """Tema em que filósofos e objeções céticas costumam entrar (mal, existência de Deus, fé e razão, ateísmo…)."""
    return _THINKERS.search(_normalize(text)) is not None


def wants_complex(text: str) -> bool:
    """A mensagem começa com a palavra "Complexo": estudo exaustivo; "tema complexo" no meio da frase não conta."""
    return _COMPLEX.search(_normalize(text)) is not None


def effort_for(text: str, study_effort: str | None) -> str | None:
    """Estudo de capítulo inteiro e pedido de opinião ganham o esforço maior; resposta breve e o resto, o padrão."""
    if study_effort is None or wants_brief(text):
        return None
    normalized = _normalize(text)
    if asks_opinion(text) or (_STUDY_VERB.search(normalized) and _WHOLE_CHAPTER.search(normalized)):
        return study_effort
    return None
