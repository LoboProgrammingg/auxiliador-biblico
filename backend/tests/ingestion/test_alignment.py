import math

from app.infrastructure.ingestion.alignment import misaligned_verses


def _unit(angle: float) -> list[float]:
    return [math.cos(angle), math.sin(angle)]


def test_misaligned_verses_clean() -> None:
    ref = [_unit(i * 0.5) for i in range(6)]
    assert misaligned_verses(ref, ref) == []


def test_misaligned_verses_detects_shift() -> None:
    ref = [_unit(i * 0.5) for i in range(6)]
    own = ref[:3] + ref[4:] + [_unit(9.0)]
    assert misaligned_verses(own, ref)[:2] == [3, 4]


def test_near_identical_refrain_not_flagged() -> None:
    ref = [_unit(0.0), _unit(0.01), _unit(0.02)]
    assert misaligned_verses(ref, ref) == []


def test_chapter_shifted_requires_consecutive_run() -> None:
    from app.infrastructure.ingestion.alignment import chapter_shifted

    ref = [_unit(i * 0.5) for i in range(6)]
    shifted = ref[:3] + ref[4:] + [_unit(9.0)]
    assert chapter_shifted(shifted, ref) is True
    isolated = list(ref)
    isolated[3] = _unit(2.0)  # parecido com o vizinho seguinte só neste versículo
    assert chapter_shifted(isolated, ref) is False
    assert chapter_shifted(ref, ref) is False
