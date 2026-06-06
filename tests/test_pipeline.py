import os
import shutil
import tempfile
import unittest

from app.orchestrator import execute
from app.pipeline import run_pipeline


class TestPipeline(unittest.TestCase):
    def test_smoke_run(self):
        products, scorecards, forecasts = run_pipeline(n=10, seed=7)
        self.assertEqual(len(products), len(scorecards))
        self.assertEqual(len(products), len(forecasts))
        self.assertGreater(len(products), 0)

    def test_decisions_in_allowed_set(self):
        _, scorecards, _ = run_pipeline(n=20, seed=11)
        allowed = {"BUY", "TEST", "WATCHLIST", "REJECT"}
        for sc in scorecards:
            self.assertIn(sc.decision, allowed)
            self.assertGreaterEqual(sc.final_score, 0)
            self.assertLessEqual(sc.final_score, 100)

    def test_forecast_metrics_present(self):
        _, _, forecasts = run_pipeline(n=5, seed=3)
        for f in forecasts:
            self.assertEqual(len(f.forecast), f.horizon)
            self.assertGreaterEqual(f.mae, 0)
            self.assertGreaterEqual(f.mape, 0)
            self.assertGreaterEqual(f.wmape, 0)

    def test_orchestrator_writes_outputs(self):
        tmp = tempfile.mkdtemp(prefix="dropbot_test_")
        try:
            products, scorecards, forecasts, summary = execute(
                n=8, seed=5, out_dir=tmp
            )
            self.assertTrue(os.path.isfile(os.path.join(tmp, "report.csv")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "report.json")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "forecasts.json")))
            self.assertEqual(sum(summary.values()), len(products))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_determinism(self):
        a = run_pipeline(n=10, seed=42)
        b = run_pipeline(n=10, seed=42)
        scores_a = [s.final_score for s in a[1]]
        scores_b = [s.final_score for s in b[1]]
        self.assertEqual(scores_a, scores_b)


if __name__ == "__main__":
    unittest.main()
