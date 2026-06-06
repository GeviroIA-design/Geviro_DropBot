def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def min_max(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return clamp((x - lo) / (hi - lo))


def to_100(x: float) -> float:
    return round(clamp(x) * 100.0, 2)
