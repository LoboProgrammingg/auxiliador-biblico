from app.domain.bible.books import BOOKS, find_book


def test_canon_has_66_books_in_protestant_order() -> None:
    assert len(BOOKS) == 66
    assert [b.id for b in BOOKS] == list(range(1, 67))
    assert BOOKS[0].pt_name == "Gênesis"
    assert BOOKS[42].pt_name == "João"
    assert BOOKS[65].abbrev == "Ap"
    assert sum(1 for b in BOOKS if b.testament == "AT") == 39


def test_codes_are_unique() -> None:
    for attr in ("osis", "step_code", "source_abbrev", "abbrev", "pt_name"):
        values = [getattr(b, attr) for b in BOOKS]
        assert len(set(values)) == 66, attr


def test_find_book_distinguishes_jo_and_job() -> None:
    assert find_book("Jo").pt_name == "João"
    assert find_book("jo").pt_name == "João"
    assert find_book("Jó").pt_name == "Jó"
    assert find_book("Job") is None or find_book("Job").pt_name == "Jó"
    assert find_book("Joao").pt_name == "João"


def test_find_book_numeric_prefixes() -> None:
    for token in ("1Jo", "1 Jo", "1º João", "1ª João", "I João", "Primeira João", "1 João"):
        assert find_book(token).id == 62, token
    assert find_book("2Sm").id == 10
    assert find_book("II Reis").id == 12


def test_find_book_unknown() -> None:
    assert find_book("Livro") is None
    assert find_book("") is None
