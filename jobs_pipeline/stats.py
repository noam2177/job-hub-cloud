from __future__ import annotations

import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    z2 = z * z
    denom = n + z2
    center = (k + z2 / 2) / denom
    margin = (z / denom) * math.sqrt((k * (n - k) / n) + z2 / 4)
    return (center - margin, center + margin)
