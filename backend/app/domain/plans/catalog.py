from dataclasses import dataclass

from app.domain.plans.reading import Reading
from app.domain.plans.themes import THEMES

ChapterSizes = dict[tuple[int, int], int]
GOSPELS = (40, 41, 42, 43)

__all__ = ["CATALOG", "PlanInfo", "Reading", "plan_days", "split_balanced"]


@dataclass(frozen=True)
class PlanInfo:
    code: str
    name: str
    description: str
    days: int


CATALOG: dict[str, PlanInfo] = {
    "biblia-1-ano": PlanInfo(
        "biblia-1-ano", "Bíblia em 1 ano", "A Bíblia inteira em ordem, com dias de tamanho parecido.", 365
    ),
    "evangelhos-30": PlanInfo(
        "evangelhos-30", "Evangelhos em 30 dias", "Mateus, Marcos, Lucas e João: a vida de Jesus em um mês.", 30
    ),
    **{code: PlanInfo(code, t.name, t.description, len(t.days)) for code, t in THEMES.items()},
}


def split_balanced(chapters: list[tuple[int, int, int]], days: int) -> list[list[tuple[int, int]]]:
    """Divide (livro, capítulo, nº de versículos) em `days` dias contíguos, parecidos em versículos; nenhum dia vazio.

    Com menos capítulos que dias, cada capítulo vira um dia."""
    if len(chapters) <= days:
        return [[(book, chapter)] for book, chapter, _ in chapters]
    total = sum(size for _, _, size in chapters)
    result: list[list[tuple[int, int]]] = [[]]
    done = 0
    for index, (book, chapter, size) in enumerate(chapters):
        result[-1].append((book, chapter))
        done += size
        day = len(result) - 1
        if day == days - 1:
            continue
        remaining_chapters = len(chapters) - index - 1
        remaining_days = days - day - 1
        target = total * (day + 1) / days
        next_size = chapters[index + 1][2] if remaining_chapters else 0
        close_enough = done + next_size / 2 >= target
        if remaining_chapters == remaining_days or (close_enough and remaining_chapters > remaining_days):
            result.append([])
    return result


def _group(day: list[tuple[int, int]]) -> list[Reading]:
    readings: list[Reading] = []
    for book, chapter in day:
        last = readings[-1] if readings else None
        if last is not None and last.book_id == book and last.chapter_end == chapter - 1:
            readings[-1] = Reading(book, last.chapter_start, chapter)
        else:
            readings.append(Reading(book, chapter, chapter))
    return readings


def plan_days(code: str, sizes: ChapterSizes) -> list[list[Reading]]:
    if code in THEMES:
        return THEMES[code].days
    books = GOSPELS if code == "evangelhos-30" else None
    chapters = [(b, c, n) for (b, c), n in sorted(sizes.items()) if books is None or b in books]
    return [_group(day) for day in split_balanced(chapters, CATALOG[code].days)]
