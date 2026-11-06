from app.application.judgments.ports import ChoiceQ, NoulQ, ScoreQ
from app.infrastructure.external.typesafe.client import JevJudge


class _A:
    def __init__(self, **kw: object) -> None:
        self.__dict__.update(kw)


class FakeSdk:
    def __init__(self) -> None:
        self.questions: dict[str, object] = {}

    async def system_one(self, state, questions, model=None):  # type: ignore[no-untyped-def]
        self.questions = dict(questions)
        return _A(
            nouls={"n": _A(noul=0.7)},
            choices={"c": _A(choice="a", confidence=0.8)},
            scores={"s": _A(score=1.5, confidence=0.6)},
            usage=_A(input_tokens=10),
        )


async def test_jev_client_maps_sdk_response() -> None:
    sdk = FakeSdk()
    answers = await JevJudge(client=sdk).ask(
        {"x": 1},
        {"n": NoulQ("é?"), "c": ChoiceQ("qual?", {"a": "A", "b": "B"}), "s": ScoreQ("quanto?", ["0", "1", "2"])},
    )
    assert answers.nouls == {"n": 0.7} and answers.choices == {"c": ("a", 0.8)} and answers.scores == {"s": (1.5, 0.6)}
    assert type(sdk.questions["c"]).__name__ == "Choice"
