from app.infrastructure.ingestion.crossrefs import CrossRefRow, parse_crossref_line


def test_parse_single_target() -> None:
    assert parse_crossref_line("Gen.1.1\tRev.4.11\t209") == CrossRefRow(1, 1, 1, 66, 4, 11, 4, 11, 209)


def test_parse_range_target() -> None:
    assert parse_crossref_line("Gen.1.1\tProv.8.22-Prov.8.30\t78") == CrossRefRow(1, 1, 1, 20, 8, 22, 8, 30, 78)


def test_parse_range_across_chapters() -> None:
    row = parse_crossref_line("Phil.4.6\tMatt.6.25-Matt.7.1\t12")
    assert row == CrossRefRow(50, 4, 6, 40, 6, 25, 7, 1, 12)


def test_header_line_ignored() -> None:
    assert parse_crossref_line("From Verse\tTo Verse\tVotes\t#www.openbible.info CC-BY 2026-11-02") is None


def test_negative_votes_skipped() -> None:
    assert parse_crossref_line("Gen.1.1\tRev.4.11\t-3") is None


def test_unknown_book_skipped() -> None:
    assert parse_crossref_line("Xyz.1.1\tRev.4.11\t3") is None
