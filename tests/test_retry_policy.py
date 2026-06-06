import unittest

from runtime.retry_policy import RetryPolicy


class TestRetryPolicy(unittest.TestCase):
    def test_should_retry_boundary(self):
        p = RetryPolicy(max_attempts=4)
        self.assertTrue(p.should_retry(1))
        self.assertTrue(p.should_retry(3))
        self.assertFalse(p.should_retry(4))
        self.assertFalse(p.should_retry(5))

    def test_exponential_backoff_sequence(self):
        p = RetryPolicy(base_delay=2.0, factor=2.0, max_delay=300.0)
        self.assertEqual(p.compute_delay(1), 2.0)
        self.assertEqual(p.compute_delay(2), 4.0)
        self.assertEqual(p.compute_delay(3), 8.0)
        self.assertEqual(p.compute_delay(4), 16.0)

    def test_delay_is_capped(self):
        p = RetryPolicy(base_delay=10.0, factor=10.0, max_delay=100.0)
        self.assertEqual(p.compute_delay(1), 10.0)
        self.assertEqual(p.compute_delay(2), 100.0)
        self.assertEqual(p.compute_delay(9), 100.0)

    def test_delay_floor(self):
        p = RetryPolicy(base_delay=2.0)
        self.assertEqual(p.compute_delay(0), 2.0)


if __name__ == "__main__":
    unittest.main()
