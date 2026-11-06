import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.passages import PassageService
from app.application.verification.final_check import final_check
from app.application.verification.markers import InvalidRefOut, MarkerStreamProcessor, TextOut, VerseOut
from app.infrastructure.database.bible_repository import SqlBibleRepository


@pytest.fixture
def repo(bible_db: AsyncSession) -> SqlBibleRepository:
    return SqlBibleRepository(bible_db)


@pytest.fixture
def proc(repo: SqlBibleRepository) -> MarkerStreamProcessor:
    return MarkerStreamProcessor(PassageService(repo))


def prose(out: list) -> str:  # type: ignore[type-arg]
    return "".join(o.text for o in out if isinstance(o, TextOut))


async def test_marker_split_across_chunks_yields_one_card(proc: MarkerStreamProcessor) -> None:
    out = await proc.feed("Leia [[Fp 2") + await proc.feed(":3|VFL]] hoje.") + await proc.flush()
    assert [type(o) for o in out if not isinstance(o, TextOut) or o.text] == [TextOut, VerseOut, TextOut]
    assert prose(out) == "Leia  hoje."
    card = next(o for o in out if isinstance(o, VerseOut))
    assert card.passage.reference == "Fp 2:3" and card.marker == "[[Fp 2:3|VFL]]"


async def test_invalid_marker_never_becomes_card(proc: MarkerStreamProcessor) -> None:
    out = await proc.feed("Veja [[Jo 1:99]] agora") + await proc.flush()
    assert not any(isinstance(o, VerseOut) for o in out)
    assert [o.marker for o in out if isinstance(o, InvalidRefOut)] == ["[[Jo 1:99]]"]
    assert prose(out) == "Veja  agora"


async def test_unterminated_marker_flushed_as_text(proc: MarkerStreamProcessor) -> None:
    out = await proc.feed("fim [[Fp 2:3") + await proc.flush()
    assert prose(out) == "fim [[Fp 2:3" and not any(isinstance(o, VerseOut) for o in out)


async def test_plain_brackets_pass_through(proc: MarkerStreamProcessor) -> None:
    out = await proc.feed("lista [a] e [b] e [[x]] ok") + await proc.flush()
    assert prose(out) == "lista [a] e [b] e  ok"
    assert [o.marker for o in out if isinstance(o, InvalidRefOut)] == ["[[x]]"]


async def test_long_bracket_run_released_as_text(proc: MarkerStreamProcessor) -> None:
    text = "[[" + "a" * 100
    out = await proc.feed(text) + await proc.flush()
    assert prose(out) == text


async def test_marker_without_translation_uses_primary(proc: MarkerStreamProcessor) -> None:
    out = await proc.feed("[[Sl 2:1]]") + await proc.flush()
    card = next(o for o in out if isinstance(o, VerseOut))
    assert card.passage.translation == "vfl"


async def test_text_without_brackets_streams_immediately(proc: MarkerStreamProcessor) -> None:
    assert prose(await proc.feed("Olá, irmão. ")) == "Olá, irmão. "


async def test_final_check_flags_nonexistent_prose_reference(repo: SqlBibleRepository) -> None:
    issues = await final_check("Como está em João 1:99, Deus cuida.", PassageService(repo), repo)
    assert [(i.kind, i.excerpt) for i in issues] == [("referencia_inexistente", "João 1:99")]


async def test_final_check_flags_fake_quote(repo: SqlBibleRepository) -> None:
    issues = await final_check(
        'A Bíblia diz: "Deus ajuda quem cedo madruga e trabalha" sempre.', PassageService(repo), repo
    )
    assert [i.kind for i in issues] == ["citacao_nao_confere"]


async def test_final_check_accepts_exact_quote_and_valid_reference(repo: SqlBibleRepository) -> None:
    issues = await final_check("Em Fp 2:3 lemos “Texto sintético Fp 2:3” com clareza.", PassageService(repo), repo)
    assert issues == []


async def test_final_check_ignores_short_quotes(repo: SqlBibleRepository) -> None:
    assert await final_check('Ele disse "graça e paz" a todos.', PassageService(repo), repo) == []


async def test_final_check_pairs_quotes_correctly(repo: SqlBibleRepository) -> None:
    prose = (
        'Primeiro "oi" e então vem uma explicação longa com muitas palavras aqui no meio "fim". '
        'Depois "Texto sintético Fp 2:3" confere.'
    )
    assert await final_check(prose, PassageService(repo), repo) == []


async def test_final_check_pairs_curly_quotes(repo: SqlBibleRepository) -> None:
    prose = "Ele disse “sim” e depois “uma frase inventada que não existe em lugar nenhum mesmo”."
    issues = await final_check(prose, PassageService(repo), repo)
    assert [i.excerpt for i in issues] == ["uma frase inventada que não existe em lugar nenhum mesmo"]


async def test_final_check_ignores_nonexistent_reference_the_user_asked_about(repo: SqlBibleRepository) -> None:
    prose = "João 1:99 não existe: o capítulo termina antes."
    issues = await final_check(prose, PassageService(repo), repo, user_text="O que diz João 1:99?")
    assert issues == []
    still = await final_check("Veja também João 1:98.", PassageService(repo), repo, user_text="O que diz João 1:99?")
    assert [i.excerpt for i in still] == ["João 1:98"]


async def test_timeline_marker_validates_sections(proc: MarkerStreamProcessor) -> None:
    from app.application.verification.markers import TimelineOut

    out = await proc.feed("Veja:\n[[linha:Sl 2|1-3=Primeira parte;4-6=Segunda") + await proc.feed(
        " parte;5-9=Fora do capítulo]]\n"
    )
    out += await proc.flush()
    timeline = next(o for o in out if isinstance(o, TimelineOut))
    assert timeline.reference == "Sl 2"
    assert timeline.sections == [
        {"start": 1, "end": 3, "title": "Primeira parte"},
        {"start": 4, "end": 6, "title": "Segunda parte"},
    ]
    assert prose(out) == "Veja:\n\n"


async def test_timeline_with_no_valid_section_is_invalid(proc: MarkerStreamProcessor) -> None:
    out = await proc.feed("[[linha:Sl 2|7-9=Nada]]") + await proc.flush()
    assert [type(o).__name__ for o in out] == ["InvalidRefOut"]


async def test_map_marker_without_places_is_dropped(proc: MarkerStreamProcessor) -> None:
    out = await proc.feed("A[[mapa:Sl 2]]B") + await proc.flush()
    assert prose(out) == "AB" and len(out) == 2


async def test_map_marker_with_places(proc: MarkerStreamProcessor, bible_db) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import text

    from app.application.verification.markers import MapOut

    await bible_db.execute(text("INSERT INTO places VALUES ('p1', 'Philippi', 'Filipos', 'settlement', 24.28, 41.01)"))
    await bible_db.execute(text("INSERT INTO place_verses (place_id, book_id, chapter, verse) VALUES ('p1', 50, 2, 3)"))
    out = await proc.feed("[[mapa:Fp 2]]") + await proc.flush()
    card = next(o for o in out if isinstance(o, MapOut))
    assert card.reference == "Fp 2" and card.places == [
        {"name": "Filipos", "kind": "settlement", "lon": 24.28, "lat": 41.01, "verses": [3]}
    ]
