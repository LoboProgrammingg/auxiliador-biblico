import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.books import BOOKS
from app.domain.bible.text import normalize_for_match

TRANSLATIONS: dict[str, str] = {
    "vfl": "Bíblia Sagrada: Versão Fácil de Ler",
    "nvt": "Nova Versão Transformadora",
    "acf": "Almeida Corrigida e Revisada Fiel",
    "ara": "Almeida Revista e Atualizada",
    "naa": "Nova Almeida Atualizada",
    "arc": "Almeida Revista e Corrigida",
    "rc69": "Almeida Revista e Corrigida 1969",
    "a21": "Almeida Século 21",
    "aa": "Almeida Revisada Imprensa Bíblica",
    "kja": "King James Atualizada",
    "bkj": "King James Fiel",
    "nvi": "Nova Versão Internacional",
    "nvi2011": "Nova Versão Internacional 2011",
    "ntlh": "Nova Tradução na Linguagem de Hoje",
    "nbv": "Nova Bíblia Viva 2007",
    "ol": "O Livro",
    "tb": "Tradução Brasileira",
    "bpt09": "Bíblia para Todos",
}
INDEXED = ("vfl", "nvt", "acf")
REFERENCE_TRANSLATION = "acf"
_BATCH = 5000

Row = tuple[int, int, int, str]


class IngestionError(Exception):
    pass


def parse_translation_json(path: Path) -> list[Row]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if len(data) != len(BOOKS):
        raise IngestionError(f"{path.name}: {len(data)} livros (esperado 66)")
    rows: list[Row] = []
    for book, entry in zip(BOOKS, data, strict=True):
        if entry["abbrev"].lower() != book.source_abbrev:
            raise IngestionError(f"{path.name}: livro {book.id} é '{entry['abbrev']}', esperado '{book.source_abbrev}'")
        for chapter_index, verses in enumerate(entry["chapters"], start=1):
            for verse_index, verse_text in enumerate(verses, start=1):
                rows.append((book.id, chapter_index, verse_index, str(verse_text).strip()))
    return rows


async def seed_books(session: AsyncSession, chapters: dict[int, int] | None = None) -> None:
    counts = chapters or {}
    for book in BOOKS:
        await session.execute(
            text(
                "INSERT INTO books (id, osis, step_code, pt_name, abbrev, testament, chapters) "
                "VALUES (:id, :osis, :step, :name, :abbrev, :testament, :chapters) "
                "ON CONFLICT (id) DO UPDATE SET chapters = GREATEST(books.chapters, EXCLUDED.chapters)"
            ),
            {
                "id": book.id,
                "osis": book.osis,
                "step": book.step_code,
                "name": book.pt_name,
                "abbrev": book.abbrev,
                "testament": book.testament,
                "chapters": counts.get(book.id, 0),
            },
        )


async def load_translation(session: AsyncSession, code: str, rows: list[Row]) -> int:
    await session.execute(
        text(
            "INSERT INTO translations (code, name, indexed) VALUES (:code, :name, :indexed) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, indexed = EXCLUDED.indexed"
        ),
        {"code": code, "name": TRANSLATIONS.get(code, code), "indexed": code in INDEXED},
    )
    await session.execute(text("DELETE FROM verses WHERE translation_code = :code"), {"code": code})
    for start in range(0, len(rows), _BATCH):
        batch = rows[start : start + _BATCH]
        await session.execute(
            text(
                "INSERT INTO verses (translation_code, book_id, chapter, verse, text, text_norm, tsv) "
                "SELECT :code, u.b, u.c, u.v, u.t, u.n, to_tsvector('portuguese', unaccent(u.t)) "
                "FROM unnest(CAST(:books AS int[]), CAST(:chapters AS int[]), CAST(:verses AS int[]), "
                "CAST(:texts AS text[]), CAST(:norms AS text[])) AS u(b, c, v, t, n)"
            ),
            {
                "code": code,
                "books": [r[0] for r in batch],
                "chapters": [r[1] for r in batch],
                "verses": [r[2] for r in batch],
                "texts": [r[3] for r in batch],
                "norms": [normalize_for_match(r[3]) for r in batch],
            },
        )
    return len(rows)


async def count_alignment(session: AsyncSession, code: str) -> int:
    await session.execute(text("DELETE FROM chapter_alignment WHERE translation_code = :code"), {"code": code})
    await session.execute(
        text(
            "INSERT INTO chapter_alignment (translation_code, book_id, chapter, ok, reason) "
            "SELECT :code, r.book_id, r.chapter, t.n IS NOT DISTINCT FROM r.n, "
            "CASE WHEN t.n IS NOT DISTINCT FROM r.n THEN NULL ELSE 'contagem' END "
            "FROM (SELECT book_id, chapter, count(*) AS n FROM verses WHERE translation_code = :ref "
            "GROUP BY book_id, chapter) r "
            "LEFT JOIN (SELECT book_id, chapter, count(*) AS n FROM verses WHERE translation_code = :code "
            "GROUP BY book_id, chapter) t USING (book_id, chapter)"
        ),
        {"code": code, "ref": REFERENCE_TRANSLATION},
    )
    failed = await session.execute(
        text("SELECT count(*) FROM chapter_alignment WHERE translation_code = :code AND NOT ok"),
        {"code": code},
    )
    return int(failed.scalar_one())
