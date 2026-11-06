import json
from dataclasses import dataclass
from typing import Any

from app.domain.bible.books import BOOKS
from app.domain.bible.entities import ResolvedPassage

ERROR_MESSAGES = {
    "texto_invalido": "A mensagem precisa ter entre 1 e 8000 caracteres.",
    "conversa_inexistente": "Conversa não encontrada.",
    "ocupado": "Ainda estou respondendo a mensagem anterior desta conversa.",
    "chave_paga_detectada": (
        "Há uma ANTHROPIC_API_KEY no ambiente. Para não gerar cobrança, remova-a ou defina PERMITIR_API_PAGA=true."
    ),
    "claude_code_indisponivel": (
        "Não consegui falar com o Claude Code. Verifique se ele está instalado e logado (rode `claude` no terminal)."
    ),
    "claude_code_login": (
        "O Claude Code desta máquina não está logado. Abra um terminal, rode `claude` e entre na sua conta."
    ),
    "limite_claude": "Você atingiu o limite de uso do Claude por agora. Tente de novo mais tarde.",
    "recusa": "Não consigo responder isso desta forma. Podemos conversar de outro jeito?",
    "agente_erro": "Algo deu errado ao gerar a resposta. Tente de novo em instantes.",
}


@dataclass(frozen=True)
class ChatEvent:
    name: str
    data: dict[str, Any]

    def encode(self) -> str:
        return f"event: {self.name}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


def error_event(code: str) -> ChatEvent:
    return ChatEvent("error", {"code": code, "message": ERROR_MESSAGES.get(code, ERROR_MESSAGES["agente_erro"])})


def passage_payload(p: ResolvedPassage) -> dict[str, Any]:
    return {
        "reference": p.reference,
        "book": BOOKS[p.range.book_id - 1].pt_name,
        "book_id": p.range.book_id,
        "chapter": p.range.chapter,
        "verse_start": p.range.verse_start,
        "verse_end": p.range.verse_end,
        "requested_translation": p.requested_translation,
        "translation": p.translation,
        "fallback_label": p.fallback_label,
        "verses": [{"n": v.verse, "text": v.text, "cited": True} for v in p.verses],
    }
