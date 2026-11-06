"""Geometria plana em graus: simplificação de linhas e recorte por caixa."""

Point = tuple[float, float]


def _distance(p: Point, a: Point, b: Point) -> float:
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return float(((x - x1) ** 2 + (y - y1) ** 2) ** 0.5)
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return float(((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** 0.5)


def simplify(points: list[Point], tolerance: float) -> list[Point]:
    """Douglas-Peucker iterativo (sem recursão profunda em costas longas)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        best, index = 0.0, -1
        for i in range(first + 1, last):
            d = _distance(points[i], points[first], points[last])
            if d > best:
                best, index = d, i
        if index != -1 and best > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    return [p for p, k in zip(points, keep, strict=True) if k]


def clamp(points: list[Point], box: tuple[float, float, float, float]) -> list[Point]:
    """Prende os pontos à caixa: polígonos enormes (continentes) viram contornos válidos e leves."""
    w, s, e, n = box
    out: list[Point] = []
    for lon, lat in points:
        p = (round(min(max(lon, w), e), 4), round(min(max(lat, s), n), 4))
        if not out or out[-1] != p:
            out.append(p)
    return out
