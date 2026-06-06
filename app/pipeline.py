from typing import List, Tuple

from analyzers import financial_analyzer, forecast_analyzer, risk_analyzer
from collectors.competitor_collector import CompetitorCollector
from collectors.marketplace_collector import MarketplaceCollector
from collectors.supplier_collector import SupplierCollector
from collectors.trends_collector import TrendsCollector
from config.settings import settings
from models.forecast import Forecast
from models.product import Product
from models.scorecard import Scorecard
from scorers.decision_rules import decide
from scorers.scoring_engine import compute_scorecard
from utils.logger import get_logger
from utils.validators import validate_product

log = get_logger("pipeline")


def _to_product(raw: dict) -> Product:
    return Product(
        product_id=raw["product_id"],
        name=raw["name"],
        category=raw["category"],
        niche=raw["niche"],
        purchase_cost=raw["purchase_cost"],
        estimated_selling_price=raw["estimated_selling_price"],
        shipping_cost=raw["shipping_cost"],
        ad_cost_estimate=raw["ad_cost_estimate"],
        demand_volume=raw["demand_volume"],
        demand_growth=raw["demand_growth"],
        short_term_momentum=raw["short_term_momentum"],
        mid_term_momentum=raw["mid_term_momentum"],
        competition_level=raw["competition_level"],
        market_saturation=raw["market_saturation"],
        average_rating=raw["average_rating"],
        review_count=raw["review_count"],
        shipping_delay_days=raw["shipping_delay_days"],
        supplier_reliability=raw["supplier_reliability"],
        estimated_return_rate=raw["estimated_return_rate"],
        seasonality_score=raw["seasonality_score"],
        demand_stability=raw["demand_stability"],
        virality_score=raw["virality_score"],
        durability_score=raw["durability_score"],
    )


def run_pipeline(
    n: int = None, seed: int = None
) -> Tuple[List[Product], List[Scorecard], List[Forecast]]:
    n = n if n is not None else settings.n_products
    seed = seed if seed is not None else settings.seed

    log.info(f"step 1/4 collecting marketplace (n={n}, seed={seed})")
    raw = MarketplaceCollector(n=n, seed=seed).collect()
    raw = TrendsCollector(seed=seed).enrich(raw)
    raw = SupplierCollector(seed=seed).enrich(raw)
    raw = CompetitorCollector(seed=seed).enrich(raw)

    log.info(f"step 2/4 building & analyzing {len(raw)} products")
    products: List[Product] = []
    for r in raw:
        p = _to_product(r)
        errs = validate_product(p)
        if errs:
            log.warning(f"product {p.product_id} dropped: {errs}")
            continue
        p = financial_analyzer.analyze(p)
        p = risk_analyzer.analyze(p)
        products.append(p)

    log.info(f"step 3/4 scoring {len(products)} products")
    scorecards: List[Scorecard] = []
    for p in products:
        sc = compute_scorecard(p)
        sc = decide(p, sc)
        scorecards.append(sc)

    log.info(f"step 4/4 forecasting {len(products)} products")
    forecasts: List[Forecast] = [
        forecast_analyzer.analyze(
            p, horizon=settings.forecast_horizon, seed=seed
        )
        for p in products
    ]

    return products, scorecards, forecasts
