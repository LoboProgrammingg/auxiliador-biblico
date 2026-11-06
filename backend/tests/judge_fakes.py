from dataclasses import dataclass, field
from typing import Any

from app.application.judgments.ports import JudgeAnswers, JudgeUnavailable


@dataclass
class FakeJudge:
    nouls: dict[str, float] = field(default_factory=dict)
    choices: dict[str, tuple[str, float]] = field(default_factory=dict)
    scores: dict[str, tuple[float, float]] = field(default_factory=dict)
    fail: bool = False
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def ask(self, state: dict[str, Any], questions: dict[str, Any]) -> JudgeAnswers:
        self.calls.append({"state": state, "questions": list(questions)})
        if self.fail:
            raise JudgeUnavailable("x")
        return JudgeAnswers(
            nouls={k: v for k, v in self.nouls.items() if k in questions},
            choices={k: v for k, v in self.choices.items() if k in questions},
            scores={k: v for k, v in self.scores.items() if k in questions},
        )
