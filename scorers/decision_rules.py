from config.constants import (
    MAX_RISK_BUY,
    MAX_SATURATION_BUY,
    MIN_DURABILITY_FOR_HYPE_OK,
    MIN_NET_MARGIN_BUY,
    MIN_SUPPLIER_RELIABILITY_BUY,
    MIN_VIRALITY_FOR_HYPE_FLAG,
    SCORE_BUY,
    SCORE_TEST,
    SCORE_WATCHLIST,
)
from models.product import Product
from models.scorecard import Scorecard


def _guards(p: Product) -> list[str]:
    g: list[str] = []
    if p.supplier_reliability < MIN_SUPPLIER_RELIABILITY_BUY:
        g.append(
            f"supplier_reliability {p.supplier_reliability:.2f} < {MIN_SUPPLIER_RELIABILITY_BUY}"
        )
    if p.risk_score > MAX_RISK_BUY:
        g.append(f"risk_score {p.risk_score:.2f} > {MAX_RISK_BUY}")
    if p.market_saturation > MAX_SATURATION_BUY:
        g.append(
            f"market_saturation {p.market_saturation:.2f} > {MAX_SATURATION_BUY}"
        )
    if p.net_margin < MIN_NET_MARGIN_BUY:
        g.append(f"net_margin {p.net_margin:.2f} < {MIN_NET_MARGIN_BUY}")
    if (
        p.virality_score > MIN_VIRALITY_FOR_HYPE_FLAG
        and p.durability_score < MIN_DURABILITY_FOR_HYPE_OK
    ):
        g.append("hype unstable: virality high, durability low")
    return g


def decide(p: Product, sc: Scorecard) -> Scorecard:
    guards = _guards(p)

    if sc.final_score >= SCORE_BUY and not guards:
        sc.decision = "BUY"
    elif sc.final_score >= SCORE_TEST and len(guards) <= 1:
        sc.decision = "TEST"
        if guards:
            sc.reasons.append(f"BUY refusé: {guards[0]}")
    elif sc.final_score >= SCORE_WATCHLIST:
        sc.decision = "WATCHLIST"
    else:
        sc.decision = "REJECT"

    for g in guards:
        sc.reasons.append(f"guard: {g}")

    return sc
