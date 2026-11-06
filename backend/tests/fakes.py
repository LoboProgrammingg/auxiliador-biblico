import hashlib


def fake_vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    raw = [b / 255 for b in digest] * 32
    norm = sum(x * x for x in raw) ** 0.5
    return [x / norm for x in raw]


class FakeEmbedder:
    async def embed(self, texts: list[str], kind: str) -> list[list[float]]:
        return [fake_vector(t) for t in texts]
