"""Windowing helpers: 5-minute incident window, median/p95, sustained crossings,
counter deltas. Owner: Backend 1."""
from __future__ import annotations

from statistics import median


def p95(values: list[float]) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


def med(values: list[float]) -> float:
    return median(values)


def sustained(values: list[float], threshold: float, min_consecutive: int = 3) -> bool:
    run = 0
    for v in values:
        run = run + 1 if v >= threshold else 0
        if run >= min_consecutive:
            return True
    return False


def counter_deltas(values: list[float]) -> tuple[list[float | None], list[int]]:
    """Cumulative counter -> per-interval deltas. Negative delta = reset: delta is
    None and its index is returned so the caller can flag counter_reset."""
    deltas: list[float | None] = []
    resets: list[int] = []
    for i in range(1, len(values)):
        d = values[i] - values[i - 1]
        if d < 0:
            deltas.append(None)
            resets.append(i)
        else:
            deltas.append(d)
    return deltas, resets
