import random
from typing import List

from models.forecast import Forecast
from models.product import Product
from utils.metrics import mae, mape, wmape


def _simulate_history(p: Product, n: int, rng: random.Random) -> List[float]:
    base = max(10.0, p.demand_volume / 30.0)
    level = base
    series: List[float] = []
    for i in range(n):
        trend = p.demand_growth * (level * 0.01)
        season = (1.0 + 0.1 * p.seasonality_score) if (i % 7 in (5, 6)) else 1.0
        noise_amp = level * (1.0 - p.demand_stability) * 0.05
        noise = rng.uniform(-noise_amp, noise_amp)
        level = max(1.0, level + trend + noise)
        series.append(round(level * season, 2))
    return series


def _naive_forecast(history: List[float], horizon: int) -> List[float]:
    if not history:
        return [0.0] * horizon
    window = history[-7:] if len(history) >= 7 else history
    avg = sum(window) / len(window)
    last = history[-1]
    if len(history) >= 7:
        trend = (history[-1] - history[-7]) / 7.0
    else:
        trend = 0.0
    return [
        round(max(0.0, (last + trend * (i + 1)) * 0.7 + avg * 0.3), 2)
        for i in range(horizon)
    ]


def analyze(
    p: Product, horizon: int = 14, history_window: int = 30, seed: int = 42
) -> Forecast:
    rng = random.Random((hash(p.product_id) & 0x7FFFFFFF) ^ seed)
    history = _simulate_history(p, history_window, rng)

    if len(history) > horizon:
        train = history[:-horizon]
        actual = history[-horizon:]
    else:
        train = history
        actual = history
    backtest = _naive_forecast(train, len(actual))

    forecast = _naive_forecast(history, horizon)

    return Forecast(
        product_id=p.product_id,
        horizon=horizon,
        historical=history,
        forecast=forecast,
        mae=round(mae(actual, backtest), 3),
        mape=round(mape(actual, backtest), 3),
        wmape=round(wmape(actual, backtest), 3),
    )
