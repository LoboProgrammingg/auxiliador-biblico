"""Catálogo dos pensadores que a IA pode citar em cartão próprio, separado do texto bíblico.

Mesma lista da skill `pensadores` (um teste confere as duas). Nome fora daqui não vira cartão.
"""

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Thinker:
    name: str
    period: str
    aliases: tuple[str, ...] = ()
    objection: bool = False


THINKERS: tuple[Thinker, ...] = (
    Thinker("Justino Mártir", "c. 100–165", ("Justino",)),
    Thinker("Ireneu de Lyon", "c. 130–202", ("Ireneu", "Irineu")),
    Thinker("Tertuliano", "c. 155–220"),
    Thinker("Orígenes", "c. 185–253"),
    Thinker("Atanásio de Alexandria", "c. 296–373", ("Atanásio",)),
    Thinker("Agostinho de Hipona", "354–430", ("Agostinho", "Santo Agostinho")),
    Thinker("Boécio", "c. 480–524"),
    Thinker("Anselmo de Cantuária", "1033–1109", ("Anselmo",)),
    Thinker("Tomás de Aquino", "1225–1274", ("Aquino", "São Tomás", "Tomás")),
    Thinker("Boaventura", "1221–1274", ("São Boaventura",)),
    Thinker("Duns Scotus", "c. 1266–1308", ("Scotus",)),
    Thinker("Martinho Lutero", "1483–1546", ("Lutero",)),
    Thinker("João Calvino", "1509–1564", ("Calvino",)),
    Thinker("René Descartes", "1596–1650", ("Descartes",)),
    Thinker("Blaise Pascal", "1623–1662", ("Pascal",)),
    Thinker("Gottfried Leibniz", "1646–1716", ("Leibniz",)),
    Thinker("Joseph Butler", "1692–1752", ("Butler",)),
    Thinker("Jonathan Edwards", "1703–1758", ("Edwards",)),
    Thinker("William Paley", "1743–1805", ("Paley",)),
    Thinker("Søren Kierkegaard", "1813–1855", ("Kierkegaard", "Soren Kierkegaard")),
    Thinker("John Henry Newman", "1801–1890", ("Newman",)),
    Thinker("Fiódor Dostoiévski", "1821–1881", ("Dostoiévski", "Dostoievski", "Dostoyevsky")),
    Thinker("G. K. Chesterton", "1874–1936", ("Chesterton",)),
    Thinker("Jacques Maritain", "1882–1973", ("Maritain",)),
    Thinker("C. S. Lewis", "1898–1963", ("Lewis", "CS Lewis")),
    Thinker("Josef Pieper", "1904–1997", ("Pieper",)),
    Thinker("Dietrich Bonhoeffer", "1906–1945", ("Bonhoeffer",)),
    Thinker("Simone Weil", "1909–1943", ("Weil",)),
    Thinker("Francis Schaeffer", "1912–1984", ("Schaeffer",)),
    Thinker("Alvin Plantinga", "1932–", ("Plantinga",)),
    Thinker("Richard Swinburne", "1934–", ("Swinburne",)),
    Thinker("John Lennox", "1943–", ("Lennox",)),
    Thinker("N. T. Wright", "1948–", ("Wright", "NT Wright", "Tom Wright")),
    Thinker("William Lane Craig", "1949–", ("Craig", "Lane Craig")),
    Thinker("Timothy Keller", "1950–2023", ("Keller", "Tim Keller")),
    Thinker("Francis Collins", "1950–", ("Collins",)),
    Thinker("Epicuro", "341–270 a.C.", objection=True),
    Thinker("David Hume", "1711–1776", ("Hume",), objection=True),
    Thinker("Ludwig Feuerbach", "1804–1872", ("Feuerbach",), objection=True),
    Thinker("Karl Marx", "1818–1883", ("Marx",), objection=True),
    Thinker("Friedrich Nietzsche", "1844–1900", ("Nietzsche",), objection=True),
    Thinker("Sigmund Freud", "1856–1939", ("Freud",), objection=True),
    Thinker("Bertrand Russell", "1872–1970", ("Russell",), objection=True),
    Thinker("Jean-Paul Sartre", "1905–1980", ("Sartre",), objection=True),
    Thinker("Albert Camus", "1913–1960", ("Camus",), objection=True),
    Thinker("Richard Dawkins", "1941–", ("Dawkins",), objection=True),
)


def _key(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower().replace(".", " "))
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


_INDEX = {_key(alias): t for t in THINKERS for alias in (t.name, *t.aliases)}


def find_thinker(name: str) -> Thinker | None:
    """Nome completo ou apelido, com ou sem acento; fora do catálogo, None."""
    return _INDEX.get(_key(name))
