import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.judgments.service import JudgmentService
from app.application.verification.facts import candidate_sentences, check_facts
from app.infrastructure.database.bible_repository import SqlBibleRepository
from tests.judge_fakes import FakeJudge


@pytest.fixture
async def repo(db_session: AsyncSession) -> SqlBibleRepository:
    from app.infrastructure.ingestion.translations import seed_books

    await seed_books(db_session)
    for pid, name in (("ruth", "Rute"), ("obed", "Obede"), ("jesse", "Jessé"), ("david", "Davi"), ("boaz", "Boaz")):
        await db_session.execute(
            text("INSERT INTO people (id, name_en, name_pt) VALUES (:i, :n, :n)"), {"i": pid, "n": name}
        )
    for child, parent in (("obed", "ruth"), ("obed", "boaz"), ("jesse", "obed"), ("david", "jesse")):
        await db_session.execute(
            text("INSERT INTO person_relations (person_id, kind, other_id) VALUES (:c, 'pai_mae', :p)"),
            {"c": child, "p": parent},
        )
    await db_session.execute(
        text("INSERT INTO person_relations (person_id, kind, other_id) VALUES ('ruth', 'conjuge', 'boaz')")
    )
    for book, verse in ((58, 1), (55, 16), (49, 11)):
        await db_session.execute(
            text(
                "INSERT INTO original_words (book_id, chapter, verse, position, surface, transliteration, gloss_en, "
                "strong, morphology, language) VALUES (:b, 1, :v, 1, 'ἔλεγχος', 'elenchos', 'proof', 'G1650', "
                "'N-NSM', 'grc')"
            ),
            {"b": book, "v": verse},
        )
    return SqlBibleRepository(db_session)


def test_prefilter_keeps_only_checkable_sentences() -> None:
    prose = (
        "Deus é fiel. Rute foi avó do rei Davi. A palavra ἔλεγχος (G1650) só aparece aqui no NT. "
        "Hoje você pode descansar. Boaz e Rute se casaram em Belém."
    )
    assert candidate_sentences(prose) == [
        "Rute foi avó do rei Davi.",
        "A palavra ἔλεγχος (G1650) só aparece aqui no NT.",
        "Boaz e Rute se casaram em Belém.",
    ]


async def test_wrong_kinship_classified_by_jev_gets_corrected(repo: SqlBibleRepository) -> None:
    jev = FakeJudge(choices={"tipo": ("parentesco", 0.95), "parentesco": ("avo", 0.9)})
    issues = await check_facts("Rute foi avó do rei Davi.", repo, JudgmentService(jev))
    assert len(issues) == 1 and issues[0]["kind"] == "fato_nao_confere"
    assert issues[0]["correction"] == "Pela base de famílias (STEPBible): Rute → Obede → Jessé → Davi."
    assert jev.calls[0]["state"]["pessoa_a"] == "Rute" and jev.calls[0]["state"]["pessoa_b"] == "Davi"


async def test_right_kinship_passes(repo: SqlBibleRepository) -> None:
    jev = FakeJudge(choices={"tipo": ("parentesco", 0.95), "parentesco": ("bisavo", 0.9)})
    assert await check_facts("Rute foi bisavó de Davi.", repo, JudgmentService(jev)) == []
    spouse = FakeJudge(choices={"tipo": ("parentesco", 0.95), "parentesco": ("conjuge", 0.9)})
    assert await check_facts("Boaz e Rute se casaram em Belém.", repo, JudgmentService(spouse)) == []


async def test_unique_occurrence_claim_is_counted_in_the_original(repo: SqlBibleRepository) -> None:
    jev = FakeJudge(choices={"tipo": ("ocorrencias", 0.9), "ocorrencias": ("unica", 0.9)})
    issues = await check_facts("A palavra ἔλεγχος (G1650) só aparece aqui no NT.", repo, JudgmentService(jev))
    assert [i["correction"] for i in issues] == [
        "No texto original, G1650 aparece em 3 versículos (Efésios, 2 Timóteo, Hebreus)."
    ]


async def test_low_confidence_or_other_kind_is_not_flagged(repo: SqlBibleRepository) -> None:
    unsure = FakeJudge(choices={"tipo": ("parentesco", 0.4), "parentesco": ("avo", 0.9)})
    assert await check_facts("Rute foi avó do rei Davi.", repo, JudgmentService(unsure)) == []
    other = FakeJudge(choices={"tipo": ("outra", 0.9)})
    assert await check_facts("Rute foi avó do rei Davi.", repo, JudgmentService(other)) == []


async def test_without_jev_the_regex_fallback_still_checks(repo: SqlBibleRepository) -> None:
    issues = await check_facts("Rute foi avó do rei Davi.", repo, JudgmentService(None))
    assert [i["kind"] for i in issues] == ["fato_nao_confere"]
    assert await check_facts("Rute foi bisavó de Davi.", repo, JudgmentService(None)) == []


async def test_unknown_people_are_never_flagged(repo: SqlBibleRepository) -> None:
    jev = FakeJudge(choices={"tipo": ("parentesco", 0.95), "parentesco": ("pai_ou_mae", 0.9)})
    assert await check_facts("Fulano foi pai de Beltrano.", repo, JudgmentService(jev)) == []
