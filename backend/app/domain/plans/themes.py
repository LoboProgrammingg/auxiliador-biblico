"""Planos temáticos: só referências (sem texto bíblico), escolhidas a dedo e conferidas no banco por teste live."""

from dataclasses import dataclass

from app.domain.plans.reading import Reading


@dataclass(frozen=True)
class Theme:
    name: str
    description: str
    days: list[list[Reading]]


def _r(book: int, chapter: int, start: int | None = None, end: int | None = None) -> list[Reading]:
    return [Reading(book, chapter, chapter, start, end)]


THEMES: dict[str, Theme] = {
    "ansiedade-provisao": Theme(
        "Ansiedade e provisão",
        "Sete dias sobre confiar no cuidado de Deus quando falta dinheiro e sobra preocupação.",
        [
            _r(40, 6, 25, 34),
            _r(50, 4, 4, 9),
            _r(60, 5, 6, 11),
            _r(19, 23),
            _r(19, 37, 1, 11),
            _r(11, 17, 1, 16),
            _r(42, 12, 22, 34),
        ],
    ),
    "perdao-recomeco": Theme(
        "Perdão e recomeço",
        "Sete dias sobre a graça que recebe de volta quem caiu.",
        [
            _r(19, 51),
            _r(42, 15, 11, 32),
            _r(62, 1, 5, 10),
            _r(43, 21, 15, 19),
            _r(40, 18, 21, 35),
            _r(23, 1, 16, 20),
            _r(51, 3, 12, 17),
        ],
    ),
    "fe-nas-provacoes": Theme(
        "Fé nas provações",
        "Sete dias com quem confiou em Deus no meio da dor.",
        [
            _r(58, 11, 1, 16),
            _r(59, 1, 2, 12),
            _r(45, 5, 1, 5),
            _r(47, 4, 7, 18),
            _r(45, 8, 28, 39),
            _r(1, 22, 1, 14),
            _r(27, 3, 13, 28),
        ],
    ),
    "familia": Theme(
        "Família",
        "Sete dias sobre casamento, filhos e lealdade em casa.",
        [
            _r(1, 2, 18, 25),
            _r(49, 5, 21, 33),
            _r(49, 6, 1, 4),
            _r(5, 6, 4, 9),
            _r(51, 3, 18, 21),
            _r(8, 1, 6, 18),
            _r(19, 127),
        ],
    ),
}
