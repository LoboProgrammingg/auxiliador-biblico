import re
import unicodedata
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Book:
    id: int
    osis: str
    step_code: str
    pt_name: str
    abbrev: str
    source_abbrev: str
    testament: Literal["AT", "NT"]


# (osis, step_code, pt_name, abbrev, source_abbrev, aliases extras — sem o número do livro)
_CANON: tuple[tuple[str, str, str, str, str, tuple[str, ...]], ...] = (
    ("Gen", "Gen", "Gênesis", "Gn", "gn", ("gen", "gên")),
    ("Exod", "Exo", "Êxodo", "Êx", "ex", ("exo",)),
    ("Lev", "Lev", "Levítico", "Lv", "lv", ("lev",)),
    ("Num", "Num", "Números", "Nm", "nm", ("num",)),
    ("Deut", "Deu", "Deuteronômio", "Dt", "dt", ("deut",)),
    ("Josh", "Jos", "Josué", "Js", "js", ("jos",)),
    ("Judg", "Jdg", "Juízes", "Jz", "jz", ("jui",)),
    ("Ruth", "Rut", "Rute", "Rt", "rt", ()),
    ("1Sam", "1Sa", "1 Samuel", "1Sm", "1sm", ("sam",)),
    ("2Sam", "2Sa", "2 Samuel", "2Sm", "2sm", ("sam",)),
    ("1Kgs", "1Ki", "1 Reis", "1Rs", "1rs", ("re",)),
    ("2Kgs", "2Ki", "2 Reis", "2Rs", "2rs", ("re",)),
    ("1Chr", "1Ch", "1 Crônicas", "1Cr", "1cr", ("crôn",)),
    ("2Chr", "2Ch", "2 Crônicas", "2Cr", "2cr", ("crôn",)),
    ("Ezra", "Ezr", "Esdras", "Ed", "ed", ("esd",)),
    ("Neh", "Neh", "Neemias", "Ne", "ne", ("nee",)),
    ("Esth", "Est", "Ester", "Et", "et", ("est",)),
    ("Job", "Job", "Jó", "Jó", "jó", ()),
    ("Ps", "Psa", "Salmos", "Sl", "sl", ("salmo", "sal")),
    ("Prov", "Pro", "Provérbios", "Pv", "pv", ("prov",)),
    ("Eccl", "Ecc", "Eclesiastes", "Ec", "ec", ("ecl",)),
    ("Song", "Sng", "Cântico dos Cânticos", "Ct", "ct", ("cantares", "cânticos", "cântico", "cant")),
    ("Isa", "Isa", "Isaías", "Is", "is", ("isa",)),
    ("Jer", "Jer", "Jeremias", "Jr", "jr", ("jer",)),
    ("Lam", "Lam", "Lamentações", "Lm", "lm", ("lam",)),
    ("Ezek", "Ezk", "Ezequiel", "Ez", "ez", ("ezeq",)),
    ("Dan", "Dan", "Daniel", "Dn", "dn", ("dan",)),
    ("Hos", "Hos", "Oseias", "Os", "os", ("oséias",)),
    ("Joel", "Jol", "Joel", "Jl", "jl", ()),
    ("Amos", "Amo", "Amós", "Am", "am", ()),
    ("Obad", "Oba", "Obadias", "Ob", "ob", ("obd",)),
    ("Jonah", "Jon", "Jonas", "Jn", "jn", ()),
    ("Mic", "Mic", "Miqueias", "Mq", "mq", ("miquéias",)),
    ("Nah", "Nam", "Naum", "Na", "na", ()),
    ("Hab", "Hab", "Habacuque", "Hc", "hc", ("hab",)),
    ("Zeph", "Zep", "Sofonias", "Sf", "sf", ("sof",)),
    ("Hag", "Hag", "Ageu", "Ag", "ag", ()),
    ("Zech", "Zec", "Zacarias", "Zc", "zc", ("zac",)),
    ("Mal", "Mal", "Malaquias", "Ml", "ml", ("mal",)),
    ("Matt", "Mat", "Mateus", "Mt", "mt", ("mat",)),
    ("Mark", "Mrk", "Marcos", "Mc", "mc", ("mar",)),
    ("Luke", "Luk", "Lucas", "Lc", "lc", ("luc",)),
    ("John", "Jhn", "João", "Jo", "jo", ()),
    ("Acts", "Act", "Atos", "At", "atos", ("atos dos apóstolos",)),
    ("Rom", "Rom", "Romanos", "Rm", "rm", ("rom",)),
    ("1Cor", "1Co", "1 Coríntios", "1Co", "1co", ("cor",)),
    ("2Cor", "2Co", "2 Coríntios", "2Co", "2co", ("cor",)),
    ("Gal", "Gal", "Gálatas", "Gl", "gl", ("gál",)),
    ("Eph", "Eph", "Efésios", "Ef", "ef", ("efé",)),
    ("Phil", "Php", "Filipenses", "Fp", "fp", ("fil", "flp")),
    ("Col", "Col", "Colossenses", "Cl", "cl", ("col",)),
    ("1Thess", "1Th", "1 Tessalonicenses", "1Ts", "1ts", ("tes",)),
    ("2Thess", "2Th", "2 Tessalonicenses", "2Ts", "2ts", ("tes",)),
    ("1Tim", "1Ti", "1 Timóteo", "1Tm", "1tm", ("tim",)),
    ("2Tim", "2Ti", "2 Timóteo", "2Tm", "2tm", ("tim",)),
    ("Titus", "Tit", "Tito", "Tt", "tt", ("tit",)),
    ("Phlm", "Phm", "Filemom", "Fm", "fm", ("filemon", "flm")),
    ("Heb", "Heb", "Hebreus", "Hb", "hb", ("heb",)),
    ("Jas", "Jas", "Tiago", "Tg", "tg", ("tia",)),
    ("1Pet", "1Pe", "1 Pedro", "1Pe", "1pe", ("ped",)),
    ("2Pet", "2Pe", "2 Pedro", "2Pe", "2pe", ("ped",)),
    ("1John", "1Jn", "1 João", "1Jo", "1jo", ()),
    ("2John", "2Jn", "2 João", "2Jo", "2jo", ()),
    ("3John", "3Jn", "3 João", "3Jo", "3jo", ()),
    ("Jude", "Jud", "Judas", "Jd", "jd", ()),
    ("Rev", "Rev", "Apocalipse", "Ap", "ap", ("apoc",)),
)

BOOKS: tuple[Book, ...] = tuple(
    Book(i, osis, step, name, abbrev, src, "AT" if i <= 39 else "NT")
    for i, (osis, step, name, abbrev, src, _) in enumerate(_CANON, start=1)
)

_PREFIX = re.compile(
    r"^(?:(?P<digit>[123])\s*[ºª°]?\s*|(?P<roman>i{1,3})\s+|(?P<word>primeir[oa]|segund[oa]|terceir[oa])\s+)(?P<rest>.+)$"
)
_WORD_NUMBERS = {"primeiro": 1, "primeira": 1, "segundo": 2, "segunda": 2, "terceiro": 3, "terceira": 3}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _split_number(token: str) -> tuple[int | None, str]:
    match = _PREFIX.match(token)
    if not match:
        return None, token
    if match["digit"]:
        number = int(match["digit"])
    elif match["roman"]:
        number = len(match["roman"])
    else:
        number = _WORD_NUMBERS[match["word"]]
    return number, match["rest"].strip()


def _build_indexes() -> tuple[dict[tuple[int | None, str], Book], dict[tuple[int | None, str], Book]]:
    exact: dict[tuple[int | None, str], Book] = {}
    for book, row in zip(BOOKS, _CANON, strict=True):
        number, base = _split_number(book.pt_name.lower())
        names = {base, *row[5]}
        for code in (book.abbrev.lower(), book.source_abbrev):
            code_number, code_base = _split_number(code)
            names.add(code_base)
            number = code_number if code_number is not None else number
        for name in names:
            exact.setdefault((number, name), book)
    loose: dict[tuple[int | None, str], Book] = {}
    for (number, name), book in exact.items():
        loose.setdefault((number, strip_accents(name)), book)
    loose[(None, "jo")] = BOOKS[42]
    return exact, loose


_EXACT, _LOOSE = _build_indexes()


def find_book(token: str) -> Book | None:
    cleaned = " ".join(token.strip().lower().rstrip(".").split())
    if not cleaned:
        return None
    number, base = _split_number(cleaned)
    return _EXACT.get((number, base)) or _LOOSE.get((number, strip_accents(base)))
