import pytest

from app.domain.bible.references import VerseRange, find_references, format_reference, parse_reference


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Jo 3:16", VerseRange(43, 3, 16, 16)),
        ("João 3.16", VerseRange(43, 3, 16, 16)),
        ("Jó 1:1", VerseRange(18, 1, 1, 1)),
        ("1Jo 1:9", VerseRange(62, 1, 9, 9)),
        ("1 Jo 1:9", VerseRange(62, 1, 9, 9)),
        ("1º João 1:9", VerseRange(62, 1, 9, 9)),
        ("I João 1:9", VerseRange(62, 1, 9, 9)),
        ("Fp 4:6-7", VerseRange(50, 4, 6, 7)),
        ("Fp 4:6–7", VerseRange(50, 4, 6, 7)),
        ("Filipenses 4.6", VerseRange(50, 4, 6, 6)),
        ("Sl 23", VerseRange(19, 23, None, None)),
        ("Salmo 23:1", VerseRange(19, 23, 1, 1)),
        ("Ct 2:4", VerseRange(22, 2, 4, 4)),
        ("Cantares 2:4", VerseRange(22, 2, 4, 4)),
        ("Jn 1:17", VerseRange(32, 1, 17, 17)),
        ("Atos 2:38", VerseRange(44, 2, 38, 38)),
        ("Gn 1:1", VerseRange(1, 1, 1, 1)),
        ("Êx 20:3", VerseRange(2, 20, 3, 3)),
        ("Ex 20:3", VerseRange(2, 20, 3, 3)),
        ("  mt 6:34 ", VerseRange(40, 6, 34, 34)),
    ],
)
def test_parse_reference_variants(text: str, expected: VerseRange) -> None:
    assert parse_reference(text) == expected


@pytest.mark.parametrize("text", ["Livro 3:16", "Jo", "Jo 3:", "Gn 1:1-2:3", "Fp 4:7-6", "Sl 0:1", "Sl 23:0", ""])
def test_parse_reference_rejects(text: str) -> None:
    assert parse_reference(text) is None


def test_format_reference() -> None:
    assert format_reference(VerseRange(50, 4, 6, 7)) == "Fp 4:6-7"
    assert format_reference(VerseRange(19, 23, None, None)) == "Sl 23"
    assert format_reference(VerseRange(43, 3, 16, 16)) == "Jo 3:16"


def test_find_references_in_prose() -> None:
    found = find_references("Como diz João 3:16 e também Fp 4.6, e o capítulo Sl 23.")
    assert [r for _, r in found] == [
        VerseRange(43, 3, 16, 16),
        VerseRange(50, 4, 6, 6),
        VerseRange(19, 23, None, None),
    ]
    assert found[0][0] == "João 3:16"


def test_find_references_ignores_plain_words() -> None:
    assert find_references("Eu fui a Atos ontem e li 3 páginas.") == []


def test_find_references_isaiah_and_numbered_books() -> None:
    found = find_references("Leia Is 53:5 e depois 1 Jo 1:9 e II Coríntios 5:17.")
    assert [r for _, r in found] == [
        VerseRange(23, 53, 5, 5),
        VerseRange(62, 1, 9, 9),
        VerseRange(47, 5, 17, 17),
    ]


@pytest.mark.parametrize(
    "prose",
    [
        "Os 20 anos de casamento",
        "Na 15 de março eu orei",
        "Am 5 minutos daqui",
        "Ez 3 mil pessoas",
        "Os atos 2 deles",
        "Números 4 e 5 são pares",
        "Is 10 vezes",
    ],
)
def test_find_references_ignores_common_words_without_verse(prose: str) -> None:
    assert find_references(prose) == []


def test_find_references_keeps_ambiguous_books_with_verse() -> None:
    assert [r for _, r in find_references("Leia Os 6:6 e Am 5:24.")] == [
        VerseRange(28, 6, 6, 6),
        VerseRange(30, 5, 24, 24),
    ]
