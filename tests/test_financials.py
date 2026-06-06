import unittest

from analyzers import financial_analyzer
from models.product import Product


def _p(**kw) -> Product:
    base = dict(
        product_id="T1", name="Test", category="home", niche="x",
        purchase_cost=5.0, estimated_selling_price=20.0, shipping_cost=2.0,
        ad_cost_estimate=3.0, demand_volume=1000, demand_growth=0.1,
        short_term_momentum=0.2, mid_term_momentum=0.1,
        competition_level=0.4, market_saturation=0.4,
        average_rating=4.5, review_count=200,
        shipping_delay_days=10, supplier_reliability=0.85,
        estimated_return_rate=0.05, seasonality_score=0.3,
        demand_stability=0.7, virality_score=0.4, durability_score=0.7,
    )
    base.update(kw)
    return Product(**base)


class TestFinancials(unittest.TestCase):
    def test_margins_positive(self):
        p = financial_analyzer.analyze(_p())
        self.assertGreater(p.gross_margin, 0)
        self.assertGreater(p.net_margin, 0)
        self.assertLessEqual(p.net_margin, p.gross_margin)

    def test_roi_positive(self):
        p = financial_analyzer.analyze(_p())
        self.assertGreater(p.roi, 0)

    def test_returns_lower_net(self):
        low_ret = financial_analyzer.analyze(_p(estimated_return_rate=0.01))
        high_ret = financial_analyzer.analyze(_p(estimated_return_rate=0.15))
        self.assertGreater(low_ret.net_profit, high_ret.net_profit)

    def test_negative_net_when_costs_exceed_price(self):
        p = financial_analyzer.analyze(
            _p(purchase_cost=15.0, ad_cost_estimate=8.0, shipping_cost=3.0)
        )
        self.assertLess(p.net_profit, 0)
        self.assertLess(p.net_margin, 0)


if __name__ == "__main__":
    unittest.main()
