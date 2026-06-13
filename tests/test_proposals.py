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


def _product(sell_price=25.0, purchase_cost=5.0, shipping_cost=2.0, **kw):
    base = dict(
        product_id="P1", name="Widget", category="home", niche="x",
        purchase_cost=purchase_cost, estimated_selling_price=sell_price,
        shipping_cost=shipping_cost, ad_cost_estimate=3.0, demand_volume=10000,
        demand_growth=0.4, short_term_momentum=0.5, mid_term_momentum=0.3,
        competition_level=0.3, market_saturation=0.3, average_rating=4.6,
        review_count=500, shipping_delay_days=9, supplier_reliability=0.9,
        estimated_return_rate=0.04, seasonality_score=0.3, demand_stability=0.8,
        virality_score=0.4, durability_score=0.75,
    )
    base.update(kw)
    return Product(**base)


def _buy(pid="P1", score=80.0):
    return Scorecard(product_id=pid, final_score=score, decision="BUY")


class TestResaleProposals(unittest.TestCase):
    def setUp(self):
        self.clk = FakeClock()
        self.store = Store(":memory:")
        self.sup = Supervisor(self.store, clock=self.clk)
        self.sup.recover()

    def tearDown(self):
        self.store.close()

    def test_generates_resale_proposal_with_positive_margin(self):
        # sell 25, supplier 7, fee 12% = 3 -> margin = 15 >= min(3)
        self.sup._generate_proposals([_product()], [_buy()])
        props = self.sup.list_proposals()
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0]["product_id"], "P1")
        self.assertGreater(props[0]["margin_per_sale"], 0)
        self.assertAlmostEqual(props[0]["platform_fee"], 3.0, places=2)

    def test_no_proposal_when_margin_below_min(self):
        # sell 8, supplier 7, fee ~0.96 -> margin ~0.04 < min(3)
        self.sup._generate_proposals(
            [_product(sell_price=8.0)], [_buy()]
        )
        self.assertEqual(self.sup.list_proposals(), [])

    def test_proposal_has_product_url(self):
        self.sup._generate_proposals([_product()], [_buy()])
        p = self.sup.list_proposals()[0]
        self.assertTrue(p["product_url"].startswith("https://"))

    def test_results_summary_for_listed(self):
        self.sup._generate_proposals([_product()], [_buy()])
        pid = self.sup.list_proposals()[0]["id"]
        self.sup.approve_proposal(pid, 1)
        res = self.sup.results_summary()
        self.assertEqual(len(res["rows"]), 1)
        self.assertGreaterEqual(res["total_sales"], 0)
        self.assertTrue(res["simulated"])

    def test_no_proposal_for_non_buy(self):
        sc = Scorecard(product_id="P1", final_score=50.0, decision="WATCHLIST")
        self.sup._generate_proposals([_product()], [sc])
        self.assertEqual(self.sup.list_proposals(), [])

    def test_dedup_same_product(self):
        self.sup._generate_proposals([_product()], [_buy()])
        self.sup._generate_proposals([_product()], [_buy()])
        self.assertEqual(len(self.sup.list_proposals()), 1)

    def test_approve_lists_on_channel(self):
        self.sup._generate_proposals([_product()], [_buy()])
        pid = self.sup.list_proposals()[0]["id"]
        ok, msg = self.sup.approve_proposal(pid, admin_id=1)
        self.assertTrue(ok)
        self.assertEqual(self.sup.proposals.get(pid)["status"], "listed")
        self.assertEqual(self.sup.metrics.get("listings_published"), 1.0)
        self.assertIn("SIMULÉE", msg)
        self.assertEqual(len(self.sup.list_listings()), 1)

    def test_reject(self):
        self.sup._generate_proposals([_product()], [_buy()])
        pid = self.sup.list_proposals()[0]["id"]
        ok, _ = self.sup.reject_proposal(pid, admin_id=1)
        self.assertTrue(ok)
        self.assertEqual(self.sup.proposals.get(pid)["status"], "rejected")

    def test_safe_mode_blocks_listing(self):
        self.sup._generate_proposals([_product()], [_buy()])
        pid = self.sup.list_proposals()[0]["id"]
        self.sup.safe_mode_on()
        ok, msg = self.sup.approve_proposal(pid, admin_id=1)
        self.assertFalse(ok)
        self.assertIn("MODE SÉCURITÉ", msg)
        self.assertEqual(self.sup.proposals.get(pid)["status"], "pending")

    def test_min_margin_blocks_approval(self):
        pid = self.sup.proposals.create(
            product_id="PX", name="Maigre", supplier_cost=9.0,
            sell_price=10.0, platform_fee=1.0, margin_per_sale=0.0, score=80.0,
        )
        ok, msg = self.sup.approve_proposal(pid, admin_id=1)
        self.assertFalse(ok)
        self.assertIn("marge", msg.lower())

    def test_scan_tags_products_for_exploration(self):
        # Chaque scan doit produire un lot étiqueté (S0000-...) -> exploration
        # de nouveaux lots, plus de blocage par déduplication.
        self.sup._handle_scan({})
        props = self.sup.list_proposals(limit=50)
        self.assertTrue(props)
        self.assertTrue(
            all(p["product_id"].startswith("S0000-") for p in props)
        )

    def test_pending_cap_blocks_new_proposals(self):
        from config.settings import Settings
        s = Settings()  # copie isolée (ne pollue pas le singleton global)
        s.max_pending_proposals = 0
        self.sup.settings = s
        self.sup._generate_proposals([_product()], [_buy()])
        self.assertEqual(self.sup.list_proposals(), [])

    def test_daily_listing_quota(self):
        self.sup.executor.max_listings_per_day = 2
        ids = [
            self.sup.proposals.create(
                product_id=f"P{i}", name=f"X{i}", supplier_cost=5.0,
                sell_price=25.0, platform_fee=3.0, margin_per_sale=17.0,
                score=80.0,
            )
            for i in range(3)
        ]
        results = [self.sup.approve_proposal(pid, 1)[0] for pid in ids]
        self.assertEqual(results.count(True), 2)
        self.assertFalse(results[-1])


if __name__ == "__main__":
    unittest.main()
