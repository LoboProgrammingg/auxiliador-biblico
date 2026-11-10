import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from app.application.bible.passages import PassageService
from app.application.bible.search import SearchService
from app.application.chat.ports import WebSearch, WebSearchUnavailable
from app.application.memory.service import MemoryService
from app.domain.bible.entities import ResolvedPassage
from app.domain.bible.errors import InvalidReference
from app.domain.bible.references import VerseRange, format_reference
from app.domain.bible.repositories import BibleRepository
from app.domain.memory.errors import InvalidMemoryContent, InvalidMemoryTopic

SERVER_NAME = "biblia"
WEB_WARNING = "Fonte externa: use só para contexto histórico/cultural; nunca como texto bíblico."
_TAGS = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class ToolOutcome:
    content: str
    is_error: bool
    status: str
    saved_memory: str | None = None


def _obj(props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


_STR = {"type": "string", "minLength": 1, "maxLength": 300}
SPECS: dict[str, tuple[str, dict[str, Any]]] = {
    "buscar_passagens": (
        "Busca passagens bíblicas por significado e por palavras (busca híbrida + rerank). Use para encontrar o que "
        "a Bíblia diz sobre um tema, situação ou sentimento. Devolve o texto exato do banco.",
        _obj({"consulta": _STR}, ["consulta"]),
    ),
    "ler_passagem": (
        "Lê o texto exato de uma referência (ex.: 'Fp 4:6-7', 'Sl 23'). Opcional: traducoes (códigos como vfl, "
        "nvt, acf, ara, naa). Use antes de citar qualquer versículo.",
        _obj({"referencia": _STR, "traducoes": {"type": "array", "items": _STR, "maxItems": 4}}, ["referencia"]),
    ),
    "original_e_lexico": (
        "Mostra o texto original palavra por palavra (hebraico/aramaico no AT, grego no NT): palavra, "
        "transliteração, número Strong, morfologia e significado do léxico.",
        _obj({"referencia": _STR}, ["referencia"]),
    ),
    "concordancia_original": (
        "Dado um número Strong (ex.: G3309, H7225G), lista onde a mesma palavra hebraica/grega aparece em outros "
        "versículos, com a forma usada. Use para mostrar 'a mesma palavra aparece em…'.",
        _obj({"strong": {"type": "string", "pattern": "^[GHgh][0-9]{1,4}[A-Za-z]?$"}}, ["strong"]),
    ),
    "comparar_traducoes": (
        "Mostra um versículo em todas as traduções disponíveis e indica quais são mais livres em relação à ACF "
        "(literal). Use quando traduções divergem; explique a diferença pelo original.",
        _obj({"referencia": _STR}, ["referencia"]),
    ),
    "referencias_cruzadas": (
        "Referências cruzadas de um versículo, trecho ou capítulo inteiro (votos somados em todo o trecho), com "
        "prévia do texto: no_outro_testamento, no_mesmo_testamento e caminhos (2º passo: o que as ligações mais fortes "
        "ligam por sua vez). Use para ligar AT e NT ('o fio da Escritura').",
        _obj({"referencia": _STR}, ["referencia"]),
    ),
    "memoria_listar": ("Lista tudo o que você lembra sobre o usuário (tópicos e conteúdo).", _obj({}, [])),
    "memoria_salvar": (
        "Cria ou substitui um tópico de memória sobre o usuário (ex.: 'situacao-financeira', 'oracao', "
        "'plano-ansiedade'). Nunca guarde CPF, senhas ou números de cartão/conta.",
        _obj(
            {
                "topico": {"type": "string", "minLength": 1, "maxLength": 60},
                "conteudo": {"type": "string", "minLength": 1, "maxLength": 4000},
            },
            ["topico", "conteudo"],
        ),
    ),
    "memoria_anotar": (
        "Acrescenta uma nota a um tópico de memória (cria o tópico se não existir). A data é adicionada "
        "automaticamente; não escreva a data na nota.",
        _obj(
            {
                "topico": {"type": "string", "minLength": 1, "maxLength": 60},
                "nota": {"type": "string", "minLength": 1, "maxLength": 1000},
            },
            ["topico", "nota"],
        ),
    ),
    "memoria_esquecer": (
        "Apaga um tópico de memória.",
        _obj({"topico": {"type": "string", "minLength": 1}}, ["topico"]),
    ),
    "pesquisar_web_serper": (
        "Pesquisa na web (Google): interpretações de estudiosos e tradições, contexto histórico, cultural ou "
        "arqueológico. Dispare as pesquisas em paralelo, na mesma rodada. No máximo 8 pesquisas por resposta; "
        "mostra quantas fontes você já reuniu. Nunca use como fonte de texto bíblico. Cite sempre o link.",
        _obj({"consulta": _STR}, ["consulta"]),
    ),
}
STATUS = {
    "buscar_passagens": "Buscando passagens…",
    "original_e_lexico": "Consultando o original…",
    "concordancia_original": "Seguindo a palavra no original…",
    "comparar_traducoes": "Comparando traduções…",
    "referencias_cruzadas": "Procurando passagens ligadas…",
    "memoria_listar": "Lembrando…",
    "memoria_salvar": "Guardando na memória…",
    "memoria_anotar": "Guardando na memória…",
    "memoria_esquecer": "Esquecendo…",
    "pesquisar_web_serper": "Pesquisando na web…",
}


def tool_names(web_serper: bool) -> list[str]:
    return [n for n in SPECS if web_serper or n != "pesquisar_web_serper"]


def allowed_tool_names(web_serper: bool) -> list[str]:
    return [f"mcp__{SERVER_NAME}__{n}" for n in tool_names(web_serper)] + ["WebSearch"]


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _covered(p: ResolvedPassage) -> set[tuple[int, int, int]]:
    return {(v.book_id, v.chapter, v.verse) for v in p.verses}


def _passage_json(p: ResolvedPassage) -> dict[str, Any]:
    return {
        "referencia": p.reference,
        "traducao": p.translation,
        "rotulo_fallback": p.fallback_label,
        "versiculos": [{"n": v.verse, "texto": v.text} for v in p.verses],
    }


MAX_WEB_SEARCHES = 8
DEFINITION_CHARS = 160
MIN_WEB_SOURCES = 4
FIRST_NT_BOOK = 40
CROSSREF_CANDIDATES, CROSSREF_OTHER, CROSSREF_SAME = 20, 10, 6
CROSSREF_HUBS, CROSSREF_HOPS = 3, 3


class ToolExecutor:
    def __init__(
        self,
        passages: PassageService,
        search: SearchService,
        repo: BibleRepository,
        memory: MemoryService,
        web: WebSearch | None,
    ) -> None:
        self._passages, self._search, self._repo, self._memory, self._web = passages, search, repo, memory, web
        self.start_turn()

    def start_turn(self) -> None:
        """Cada resposta tem sua própria cota de pesquisas na web."""
        self._web_searches = 0
        self._web_sources: set[str] = set()

    async def run(self, name: str, args: dict[str, Any]) -> ToolOutcome:
        handler = getattr(self, f"_t_{name}", None)
        if handler is None or (name == "pesquisar_web_serper" and self._web is None):
            return ToolOutcome(f"ferramenta desconhecida: {name}", True, "…")
        status = f"Lendo {args.get('referencia', '')}…" if name == "ler_passagem" else STATUS.get(name, "…")
        try:
            content, saved = await handler(args)
        except InvalidReference as exc:
            return ToolOutcome(str(exc), True, status)
        except (InvalidMemoryTopic, InvalidMemoryContent) as exc:
            return ToolOutcome(f"memória inválida: {exc}", True, status)
        except WebSearchUnavailable:
            return ToolOutcome("pesquisa web indisponível agora", True, status)
        return ToolOutcome(content, False, status, saved)

    async def _t_buscar_passagens(self, a: dict[str, Any]) -> tuple[str, str | None]:
        return _dump([_passage_json(p) for p in await self._search.search(a["consulta"], 8)]), None

    async def _t_ler_passagem(self, a: dict[str, Any]) -> tuple[str, str | None]:
        codes = a.get("traducoes") or [None]
        return _dump([_passage_json(await self._passages.resolve(a["referencia"], c)) for c in codes]), None

    async def _t_original_e_lexico(self, a: dict[str, Any]) -> tuple[str, str | None]:
        base = await self._passages.resolve(a["referencia"])
        words = await self._repo.original_words(base.range)
        lex = await self._repo.lexicon([w.strong for w in words])
        out = [
            {
                "versiculo": w.verse,
                "palavra": w.surface,
                "transliteracao": w.transliteration,
                "strong": w.strong,
                "morfologia": w.morphology,
                "lingua": w.language,
                "glosa_contexto_en": w.gloss_en,
                "lema": lex[w.strong].lemma if w.strong in lex else None,
                "significado_en": lex[w.strong].gloss if w.strong in lex else None,
                "definicao": _TAGS.sub("", lex[w.strong].definition)[:DEFINITION_CHARS].strip()
                if w.strong in lex
                else None,
            }
            for w in words
        ]
        return _dump({"referencia": base.reference, "palavras": out}), None

    async def _t_concordancia_original(self, a: dict[str, Any]) -> tuple[str, str | None]:
        strong = a["strong"][0].upper() + a["strong"][1:]
        hits = await self._repo.verses_with_strong(strong, 30)
        items = []
        for r, surface in hits:
            try:
                text = (await self._passages.resolve(r)).verses[0].text
            except InvalidReference:
                continue
            items.append({"referencia": format_reference(r), "palavra": surface, "texto": text})
        lex = (await self._repo.lexicon([strong])).get(strong)
        return _dump({"strong": strong, "lema": lex.lemma if lex else None, "ocorrencias": items}), None

    async def _t_comparar_traducoes(self, a: dict[str, Any]) -> tuple[str, str | None]:
        base = await self._passages.resolve(a["referencia"])
        r = base.range
        verses = await self._repo.verse_in_all_translations(r.book_id, r.chapter, r.verse_start or 1)
        names = await self._repo.translation_names()
        literal = next((v.text for v in verses if v.translation == "acf"), "")
        items = [
            {
                "traducao": v.translation,
                "nome": names.get(v.translation, v.translation),
                "texto": v.text,
                "proximidade_acf": round(SequenceMatcher(None, literal.lower(), v.text.lower()).ratio(), 2),
            }
            for v in verses
        ]
        return _dump({"referencia": format_reference(r), "traducoes": items}), None

    async def _linked(
        self, r: VerseRange, seen: set[tuple[int, int, int]], limit: int
    ) -> list[tuple[VerseRange, dict[str, Any]]]:
        """Ligações que não repetem versículo já visto, com prévia do texto (o que chega aqui conta como lido)."""
        out: list[tuple[VerseRange, dict[str, Any]]] = []
        for ref in await self._repo.range_cross_references(r, limit * 2 + 10):
            try:
                preview = await self._passages.resolve(ref.target)
            except InvalidReference:
                continue
            covered = _covered(preview)
            if covered & seen:
                continue
            seen |= covered
            out.append(
                (ref.target, {"referencia": preview.reference, "votos": ref.votes, "texto": preview.verses[0].text})
            )
            if len(out) == limit:
                break
        return out

    async def _t_referencias_cruzadas(self, a: dict[str, Any]) -> tuple[str, str | None]:
        base = await self._passages.resolve(a["referencia"])
        seen = _covered(base)
        linked = await self._linked(base.range, seen, CROSSREF_CANDIDATES)
        is_ot = base.range.book_id < FIRST_NT_BOOK
        other = [item for r, item in linked if (r.book_id < FIRST_NT_BOOK) != is_ot]
        same = [item for r, item in linked if (r.book_id < FIRST_NT_BOOK) == is_ot]
        paths = []
        for r, hub in linked[:CROSSREF_HUBS]:
            if hops := await self._linked(r, seen, CROSSREF_HOPS):
                paths.append({"via": hub["referencia"], "ligadas": [item for _, item in hops]})
        return _dump(
            {
                "referencia": base.reference,
                "no_outro_testamento": other[:CROSSREF_OTHER],
                "no_mesmo_testamento": same[:CROSSREF_SAME],
                "caminhos": paths,
            }
        ), None

    async def _t_memoria_listar(self, a: dict[str, Any]) -> tuple[str, str | None]:
        items = await self._memory.list_all()
        return _dump(
            [{"topico": i.topic, "conteudo": i.content, "atualizado_em": i.updated_at.isoformat()} for i in items]
        ), None

    async def _t_memoria_salvar(self, a: dict[str, Any]) -> tuple[str, str | None]:
        topic = await self._memory.save(a["topico"], a["conteudo"])
        return f"guardado em '{topic}'", topic

    async def _t_memoria_anotar(self, a: dict[str, Any]) -> tuple[str, str | None]:
        topic = await self._memory.append(a["topico"], a["nota"])
        return f"anotado em '{topic}'", topic

    async def _t_memoria_esquecer(self, a: dict[str, Any]) -> tuple[str, str | None]:
        removed = await self._memory.forget(a["topico"])
        return ("esquecido" if removed else "tópico não existia"), None

    async def _t_pesquisar_web_serper(self, a: dict[str, Any]) -> tuple[str, str | None]:
        assert self._web is not None
        if self._web_searches >= MAX_WEB_SEARCHES:
            return (
                f"limite de {MAX_WEB_SEARCHES} pesquisas nesta resposta atingido: conclua com o que já reuniu, "
                "com os versículos como base."
            ), None
        self._web_searches += 1
        results = await self._web.search(a["consulta"], 5)
        self._web_sources |= {r.link for r in results if r.link}
        return _dump(
            {
                "aviso": WEB_WARNING,
                "resultados": [{"titulo": r.title, "link": r.link, "trecho": r.snippet} for r in results],
                "fontes_reunidas": len(self._web_sources),
                "fontes_minimas": MIN_WEB_SOURCES,
                "pesquisas_restantes": MAX_WEB_SEARCHES - self._web_searches,
            }
        ), None


def build_mcp_server(
    executor: ToolExecutor, on_outcome: Callable[[ToolOutcome], Awaitable[None]], web_serper: bool
) -> McpSdkServerConfig:
    def make(name: str) -> Any:
        description, schema = SPECS[name]

        @tool(name, description, schema)
        async def handler(args: dict[str, Any]) -> dict[str, Any]:
            outcome = await executor.run(name, args)
            await on_outcome(outcome)
            return {"content": [{"type": "text", "text": outcome.content}], "is_error": outcome.is_error}

        return handler

    return create_sdk_mcp_server(SERVER_NAME, "1.0.0", [make(n) for n in tool_names(web_serper)])
