import re
import unicodedata

_STUDY_VERB = re.compile(r"\b(?:interpret\w*|estud\w*|expli[cq]\w*|entender)\b")
_OPINION = re.compile(
    r"\b(?:na sua (?:opiniao|visao)|(?:qual|e) (?:e )?(?:a )?sua (?:opiniao|visao|interpretacao|leitura)"
    r"|o que (?:voce|vc|tu) (?:acha|pensa|entende)|(?:voce|vc) acredita)\b"
)
_WHOLE_CHAPTER = re.compile(r"\bcapitulo\s+\d{1,3}\b|\b[a-z]{2,}\s+\d{1,3}\b(?!\s*[:.,]\s*\d)")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def asks_opinion(text: str) -> bool:
    """A pessoa quer a opinião e a interpretação do próprio auxiliador (na sua opinião, o que você acha…)."""
    return _OPINION.search(_normalize(text)) is not None


def effort_for(text: str, study_effort: str | None) -> str | None:
    """Estudo de capítulo inteiro e pedido de opinião recebem o esforço maior; o resto usa o padrão (None)."""
    if study_effort is None:
        return None
    normalized = _normalize(text)
    if asks_opinion(text) or (_STUDY_VERB.search(normalized) and _WHOLE_CHAPTER.search(normalized)):
        return study_effort
    return None
