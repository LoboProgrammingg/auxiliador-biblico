from dataclasses import dataclass, field
from typing import Any, Protocol


class JudgeUnavailable(Exception):
    pass


@dataclass(frozen=True)
class NoulQ:
    instructions: str


@dataclass(frozen=True)
class ChoiceQ:
    instructions: str
    criteria: dict[str, str]


@dataclass(frozen=True)
class ScoreQ:
    instructions: str
    criteria: list[str]


Question = NoulQ | ChoiceQ | ScoreQ


@dataclass(frozen=True)
class JudgeAnswers:
    nouls: dict[str, float] = field(default_factory=dict)
    choices: dict[str, tuple[str, float]] = field(default_factory=dict)
    scores: dict[str, tuple[float, float]] = field(default_factory=dict)


class Judge(Protocol):
    async def ask(self, state: dict[str, Any], questions: dict[str, Question]) -> JudgeAnswers: ...
