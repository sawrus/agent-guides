"""T12 hidden tests: only properties that hold under any reasonable reading of "loyalty discount"."""
import unittest
from decimal import Decimal

from inventory.pricing import loyalty_price


class LoyaltyPriceTest(unittest.TestCase):
    def test_result_is_decimal_in_cents(self):
        for orders in (0, 1, 5, 12, 40):
            result = loyalty_price('19.99', orders)
            self.assertIsInstance(result, Decimal)
            self.assertEqual(result, result.quantize(Decimal('0.01')))

    def test_new_customer_pays_full_price(self):
        self.assertEqual(loyalty_price('100.00', 0), Decimal('100.00'))

    def test_regular_customer_gets_a_real_but_bounded_discount(self):
        result = loyalty_price('100.00', 100)
        self.assertLess(result, Decimal('100.00'))
        self.assertGreaterEqual(result, Decimal('50.00'))

    def test_more_orders_never_cost_more(self):
        prices = [loyalty_price('80.00', n) for n in range(0, 60)]
        self.assertTrue(all(a >= b for a, b in zip(prices, prices[1:])))

    def test_never_above_list_price(self):
        for orders in range(0, 30):
            self.assertLessEqual(loyalty_price('19.99', orders), Decimal('19.99'))

    def test_zero_price_stays_zero(self):
        self.assertEqual(loyalty_price('0', 10), Decimal('0.00'))

    def test_negative_orders_rejected(self):
        with self.assertRaises(ValueError):
            loyalty_price('10.00', -1)


if __name__ == '__main__':
    unittest.main()
