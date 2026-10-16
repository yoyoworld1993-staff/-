import unittest
from core import calculate

class CalculationTests(unittest.TestCase):
    def test_basic_profit_and_cap(self):
        cost, profit, cap = calculate(1000, 0.045, 0, 5, 45, 200, 10, 10, 50)
        self.assertEqual(cost, 102.25)
        self.assertEqual(profit, 77.75)
        self.assertEqual(cap, 1587)

    def test_invalid_exchange_rate(self):
        with self.assertRaises(ValueError):
            calculate(1000, 0, 0, 5, 45, 200, 10, 10, 50)

    def test_overbudget_max_bid_zero(self):
        _, _, cap = calculate(5000, 0.045, 0, 5, 60, 100, 10, 10, 50)
        self.assertEqual(cap, 0)

if __name__ == "__main__":
    unittest.main()
