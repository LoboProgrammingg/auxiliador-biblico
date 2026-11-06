from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.books import BOOKS
from app.infrastructure.ingestion.stepbible import (
    load_lexicon_file,
    load_word_file,
    parse_lexicon_line,
    parse_tagnt_line,
    parse_tahot_line,
)
from app.infrastructure.ingestion.translations import seed_books

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_tagnt_word() -> None:
    line = (
        "Mat.6.34#03=NKO\tμεριμνήσητε (merimnēsēte)\tshall you be anxious\tG3309=V-AAS-2P\t"
        "μεριμνάω=to worry\tNA28+NA27+Tyn+SBL+WH+Treg+TR+Byz\t\t\ttengan ansiedad"
    )
    w = parse_tagnt_line(line)
    assert w is not None
    assert (w.book_id, w.chapter, w.verse, w.position) == (40, 6, 34, 3)
    assert w.surface == "μεριμνήσητε" and w.transliteration == "merimnēsēte"
    assert w.strong == "G3309" and w.morphology == "V-AAS-2P" and w.language == "grc"
    assert w.gloss_en == "shall you be anxious"


def test_parse_tahot_uses_english_versification_and_braced_strong() -> None:
    line = "Gen.31.55(32.1)#01=L\tוַ/יַּשְׁכֵּ֨ם\tva/i.yash.Kem\tand/ he rose early\tH9001/{H7925}\tHc/Vhw3ms\t\t"
    w = parse_tahot_line(line)
    assert w is not None
    assert (w.book_id, w.chapter, w.verse, w.position) == (1, 31, 55, 1)
    assert w.strong == "H7925" and w.language == "heb" and w.transliteration == "va/i.yash.Kem"


def test_parse_tahot_detects_aramaic() -> None:
    w = parse_tahot_line("Dan.2.5#01=L\tעָנֵ֤ה\t'a.Neh\t[was] replying\t{H6032}\tAVqrmsa\t\t")
    assert w is not None and w.language == "arc" and w.book_id == 27


def test_parse_lexicon_line_uses_dstrong_key() -> None:
    entry = parse_lexicon_line(
        "H7225\tH7225H = a Meaning of\tH7225G\tרֵאשִׁית\tre.shit\tH:N-F\tfirst: best\t: best<br>1) first"
    )
    assert entry is not None and entry.strong == "H7225H" and entry.gloss == "first: best"
    greek = parse_lexicon_line("G3309\tG3309 =\tG3309\tμεριμνάω\tmerimnaō\tG:V\tto worry\t<b>μεριμνάω</b>")
    assert greek is not None and greek.strong == "G3309" and greek.lemma == "μεριμνάω"


def test_header_comment_and_blank_lines_are_ignored() -> None:
    assert parse_tagnt_line("") is None
    assert parse_tagnt_line("# Mat.6.34\tμὴ") is None
    assert parse_tagnt_line("Word & Type\tGreek\tEnglish") is None
    assert parse_tahot_line("Eng (Heb) Ref & Type\tHebrew") is None
    assert parse_lexicon_line("eStrong#\tThis is the standard") is None


def test_step_codes_known_by_canon() -> None:
    codes = {b.step_code for b in BOOKS}
    for name in ("tagnt_amostra.txt", "tahot_amostra.txt"):
        for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines():
            parser = parse_tagnt_line if name.startswith("tagnt") else parse_tahot_line
            if parser(line) is not None:
                assert line.split(".", 1)[0] in codes


async def test_load_files_insert_rows(db_session: AsyncSession) -> None:
    await seed_books(db_session)
    assert await load_word_file(db_session, FIXTURES / "tagnt_amostra.txt", parse_tagnt_line) == 6
    assert await load_word_file(db_session, FIXTURES / "tahot_amostra.txt", parse_tahot_line) == 4
    assert await load_lexicon_file(db_session, FIXTURES / "lexicon_amostra.txt") == 3
    langs = await db_session.execute(text("SELECT language, count(*) FROM original_words GROUP BY 1 ORDER BY 1"))
    assert langs.all() == [("arc", 1), ("grc", 6), ("heb", 3)]
