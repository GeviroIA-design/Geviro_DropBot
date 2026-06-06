import unittest

from app.supervisor import Supervisor
from models.product import Product
from models.scorecard import Scorecard
from runtime.service_state import Store


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def _product(net_profit=8.0, net_margin=0.32, **kw):
    base = dict(
        product_id="P1", name="Widget", category="home", niche="x",
        purchase_cost=5.0, estimated_selling_price=25.0, shipping_cost=2.0,
        ad_cost_estimate=3.0, demand_volume=10000, demand_growth=0.4,
        short_term_momentum=0.5, mid_term_momentum=0.3,
        competition_level=0.3, market_saturation=0.3, average_rating=4.6,
        review_count=500, shipping_delay_days=9, supplier_reliability=0.9,
        estimated_return_rate=0.04, seasonality_score=0.3, demand_stability=0.8,
        virality_score=0.4, durability_score=0.75,
    )
    base.update(kw)
    p = Product(**base)
    p.net_profit = net_profit
    p.net_margin = net_margin
    return p


def _buy(pid="P1", score=80.0):
    return Scorecard(product_id=pid, final_score=score, decision="BUY")


class TestProposals(unittest.TestCase):
    def setUp(self):
        self.clk = FakeClock()
        self.store = Store(":memory:")
        self.sup = Supervisor(self.store, clock=self.clk)
        self.sup.recover()

    def tearDown(self):
        self.store.close()

    def test_generates_for_buy_with_positive_gain(self):
        self.sup._generate_proposals([_product()], [_buy()])
        props = self.sup.list_proposals()
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0]["product_id"], "P1")
        self.assertGreater(props[0]["expected_gain"], 0)

    def test_no_proposal_for_non_buy(self):
        sc = Scorecard(product_id="P1", final_score=50.0, decision="WATCHLIST")
        self.sup._generate_proposals([_product()], [sc])
        self.assertEqual(self.sup.list_proposals(), [])

    def test_no_proposal_when_gain_not_positive(self):
        self.sup._generate_proposals([_product(net_profit=-1.0)], [_buy()])
        self.assertEqual(self.sup.list_proposals(), [])

    def test_dedup_same_product(self):
        self.sup._generate_proposals([_product()], [_buy()])
        self.sup._generate_proposals([_product()], [_buy()])
        self.assertEqual(len(self.sup.list_proposals()), 1)

    def test_approve_executes_within_limits(self):
        self.sup._generate_proposals([_product()], [_buy()])
        pid = self.sup.list_proposals()[0]["id"]
        ok, msg = self.sup.approve_proposal(pid, admin_id=1)
        self.assertTrue(ok)
        self.assertEqual(self.sup.proposals.get(pid)["status"], "executed")
        self.assertEqual(self.sup.metrics.get("orders_executed"), 1.0)
        self.assertIn("SIMULEE", msg)  # pas d'API reelle branchee

    def test_reject(self):
        self.sup._generate_proposals([_product()], [_buy()])
        pid = self.sup.list_proposals()[0]["id"]
        ok, _ = self.sup.reject_proposal(pid, admin_id=1)
        self.assertTrue(ok)
        self.assertEqual(self.sup.proposals.get(pid)["status"], "rejected")

    def test_safe_mode_blocks_approval(self):
        self.sup._generate_proposals([_product()], [_buy()])
        pid = self.sup.list_proposals()[0]["id"]
        self.sup.safe_mode_on()
        ok, msg = self.sup.approve_proposal(pid, admin_id=1)
        self.assertFalse(ok)
        self.assertIn("SAFE MODE", msg)
        self.assertEqual(self.sup.proposals.get(pid)["status"], "pending")

    def test_budget_cap_blocks_approval(self):
        pid = self.sup.proposals.create(
            product_id="PX", name="Cher", quantity=100, unit_cost=50.0,
            unit_sell_price=80.0, expected_unit_net=20.0, expected_gain=2000.0,
            order_cost=5000.0, score=90.0,
        )
        ok, msg = self.sup.approve_proposal(pid, admin_id=1)
        self.assertFalse(ok)
        self.assertIn("plafond", msg)

    def test_daily_quota_enforced(self):
        ids = [
            self.sup.proposals.create(
                product_id=f"P{i}", name=f"X{i}", quantity=1, unit_cost=10.0,
                unit_sell_price=20.0, expected_unit_net=5.0, expected_gain=5.0,
                order_cost=10.0, score=80.0,
            )
            for i in range(self.sup.settings.max_orders_per_day + 1)
        ]
        results = [self.sup.approve_proposal(pid, 1)[0] for pid in ids]
        self.assertEqual(
            results.count(True), self.sup.settings.max_orders_per_day
        )
        self.assertFalse(results[-1])


if __name__ == "__main__":
    unittest.main()
