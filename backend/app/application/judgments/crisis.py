import re
import unicodedata

_RISK = re.compile(
    "|".join(
        [
            r"\bme matar\b",
            r"\bme suicidar\b",
            r"\b(?:penso|pensando|pensei|pensamentos?|ideias?|vontade|quero|vou|tentei|tentar)\b[^.!?]{0,30}\bsuicid",
            r"\btirar (?:a )?minha (?:propria )?vida\b",
            r"\b(?:acabar com|dar (?:um )?fim a|por (?:um )?fim a|terminar com) (?:a )?minha (?:propria )?vida\b",
            r"\bnao (?:quero|aguento|consigo) mais viver\b",
            r"\b(?:quero|vontade de|queria) morrer\b",
            r"\bqueria (?:estar|ter) mort[oa]\b",
            r"\bmelhor (?:eu )?(?:morrer|estar mort[oa])\b",
            r"\bme (?:cortar|machucar|ferir)\b",
            r"\bsumir (?:para|pra) sempre\b",
            r"\bsem (?:motivo|razao|sentido) (?:para|pra|de) viver\b",
        ]
    )
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def detect_crisis(text: str) -> bool:
    """Expressões de risco à vida; funciona sem o Jev, como rede de segurança."""
    return _RISK.search(_normalize(text)) is not None
