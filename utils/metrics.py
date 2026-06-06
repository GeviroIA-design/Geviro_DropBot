from typing import List


def mae(actual: List[float], predicted: List[float]) -> float:
    if not actual:
        return 0.0
    n = min(len(actual), len(predicted))
    if n == 0:
        return 0.0
    return sum(abs(actual[i] - predicted[i]) for i in range(n)) / n


def mape(actual: List[float], predicted: List[float]) -> float:
    if not actual:
        return 0.0
    n = min(len(actual), len(predicted))
    errs = []
    for i in range(n):
        if actual[i] == 0:
            continue
        errs.append(abs((actual[i] - predicted[i]) / actual[i]))
    return (sum(errs) / len(errs)) * 100.0 if errs else 0.0


def wmape(actual: List[float], predicted: List[float]) -> float:
    if not actual:
        return 0.0
    n = min(len(actual), len(predicted))
    denom = sum(abs(actual[i]) for i in range(n))
    if denom == 0:
        return 0.0
    num = sum(abs(actual[i] - predicted[i]) for i in range(n))
    return (num / denom) * 100.0
