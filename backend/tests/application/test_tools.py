import json

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.passages import PassageService
from app.application.bible.search import SearchService
from app.application.chat.ports import RerankUnavailable, WebResult
from app.application.chat.tools import ToolExecutor, allowed_tool_names, build_mcp_server, tool_names
from app.application.memory.service import MemoryService
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.database.memory_repository import SqlMemoryRepository
from tests.fakes import FakeEmbedder


class NoRerank:
    async def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        raise RerankUnavailable("x")


class FakeWeb:
    async def search(self, query: str, num: int = 5) -> list[WebResult]:
        return [WebResult("Filipos", "https://exemplo.org/filipos", "colônia romana")]


@pytest.fixture
def executor(bible_db: AsyncSession) -> ToolExecutor:
    repo = SqlBibleRepository(bible_db)
    passages = PassageService(repo)
    return ToolExecutor(
        passages=passages,
        search=SearchService(repo, passages, FakeEmbedder(), NoRerank()),
        repo=repo,
        memory=MemoryService(SqlMemoryRepository(bible_db)),
        web=FakeWeb(),
    )


def test_tool_names_without_serper() -> None:
    names = tool_names(web_serper=False)
    assert "pesquisar_web_serper" not in names and "concordancia_original" in names and len(names) == 10
    allowed = allowed_tool_names(web_serper=False)
    assert "mcp__biblia__ler_passagem" in allowed and "WebSearch" in allowed
    assert "WebFetch" not in allowed  # evita vazamento de memória pela URL
    assert "pesquisar_web_serper" in tool_names(web_serper=True)


async def test_ler_passagem_returns_db_text_and_fallback_label(executor: ToolExecutor) -> None:
    out = await executor.run("ler_passagem", {"referencia": "Jo 2:3"})
    data = json.loads(out.content)
    assert not out.is_error and out.status == "Lendo Jo 2:3…"
    assert data[0]["traducao"] == "nvt" and data[0]["rotulo_fallback"] == "NVT — VFL indisponível neste trecho"
    assert data[0]["versiculos"] == [{"n": 3, "texto": "Texto sintético Jo 2:3"}]


async def test_ler_passagem_multiple_translations(executor: ToolExecutor) -> None:
    data = json.loads(
        (await executor.run("ler_passagem", {"referencia": "Fp 1:1", "traducoes": ["acf", "vfl"]})).content
    )
    assert [d["traducao"] for d in data] == ["acf", "vfl"]


async def test_invalid_reference_is_tool_error_not_exception(executor: ToolExecutor) -> None:
    out = await executor.run("ler_passagem", {"referencia": "Jo 1:99"})
    assert out.is_error and "referência não encontrada" in out.content


async def test_unknown_tool_is_error(executor: ToolExecutor) -> None:
    assert (await executor.run("rm_rf", {})).is_error


async def test_memoria_salvar_reports_saved_memory(executor: ToolExecutor) -> None:
    out = await executor.run("memoria_salvar", {"topico": "Família", "conteudo": "Casado."})
    assert out.saved_memory == "familia" and not out.is_error
    listed = json.loads((await executor.run("memoria_listar", {})).content)
    assert listed == [{"topico": "familia", "conteudo": "Casado.", "atualizado_em": listed[0]["atualizado_em"]}]
    note = await executor.run("memoria_anotar", {"topico": "familia", "nota": "filho nasceu"})
    assert note.saved_memory == "familia"
    assert not (await executor.run("memoria_esquecer", {"topico": "familia"})).is_error


async def test_concordancia_returns_verses_sharing_strong(executor: ToolExecutor, bible_db: AsyncSession) -> None:
    await bible_db.execute(
        text(
            "INSERT INTO original_words (book_id, chapter, verse, position, surface, transliteration, gloss_en, "
            "strong, morphology, language) VALUES (50, 2, 3, 1, 'μεριμνᾶτε', 'merimnate', 'be anxious', 'G3309', "
            "'V', 'grc'), (42, 1, 2, 1, 'μεριμνᾷς', 'merimnas', 'are anxious', 'G3309', 'V', 'grc')"
        )
    )
    data = json.loads((await executor.run("concordancia_original", {"strong": "g3309"})).content)
    assert [d["referencia"] for d in data["ocorrencias"]] == ["Lc 1:2", "Fp 2:3"]
    assert data["ocorrencias"][1]["palavra"] == "μεριμνᾶτε" and data["ocorrencias"][1]["texto"]


async def test_comparar_traducoes_skips_misaligned_chapters(executor: ToolExecutor) -> None:
    data = json.loads((await executor.run("comparar_traducoes", {"referencia": "Jo 2:1"})).content)
    assert {d["traducao"] for d in data["traducoes"]} == {"acf", "nvt"}


async def test_original_e_lexico_includes_gloss(executor: ToolExecutor, bible_db: AsyncSession) -> None:
    await bible_db.execute(
        text(
            "INSERT INTO original_words (book_id, chapter, verse, position, surface, transliteration, gloss_en, "
            "strong, morphology, language) VALUES (50, 2, 3, 1, 'μεριμνᾶτε', 'merimnate', 'be anxious', 'G3309', "
            "'V-PAM-2P', 'grc')"
        )
    )
    await bible_db.execute(
        text("INSERT INTO lexicon VALUES ('G3309', 'μεριμνάω', 'merimnaō', 'to worry', '<b>x</b> y')")
    )
    data = json.loads((await executor.run("original_e_lexico", {"referencia": "Fp 2:3"})).content)
    word = data["palavras"][0]
    assert word["strong"] == "G3309" and word["lema"] == "μεριμνάω" and word["definicao"] == "x y"


async def test_web_search_includes_warning(executor: ToolExecutor) -> None:
    out = await executor.run("pesquisar_web_serper", {"consulta": "Filipos"})
    assert "nunca como texto bíblico" in out.content and "https://exemplo.org/filipos" in out.content


async def test_build_mcp_server_wraps_all_tools(executor: ToolExecutor) -> None:
    seen = []

    async def on_outcome(outcome):  # type: ignore[no-untyped-def]
        seen.append(outcome)

    server = build_mcp_server(executor, on_outcome, web_serper=False)
    assert server["name"] == "biblia"


async def test_parallel_tool_calls_share_session_safely(executor: ToolExecutor) -> None:
    import asyncio

    outcomes = await asyncio.gather(
        *[executor.run("ler_passagem", {"referencia": f"Fp {c}:{v}"}) for c in (1, 2) for v in (1, 2, 3)],
        executor.run("comparar_traducoes", {"referencia": "Jo 1:1"}),
        executor.run("referencias_cruzadas", {"referencia": "Fp 2:3"}),
    )
    assert not any(o.is_error for o in outcomes), [o.content for o in outcomes if o.is_error]
