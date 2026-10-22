import unittest
from decimal import Decimal

from inventory.pricing import apply_discount, order_total, to_money


class PricingTest(unittest.TestCase):
    def test_to_money_rounds_half_up(self):
        self.assertEqual(to_money('2.345'), Decimal('2.35'))

    def test_no_discount(self):
        self.assertEqual(apply_discount('10.00', 0), Decimal('10.00'))

    def test_full_discount(self):
        self.assertEqual(apply_discount('10.00', 100), Decimal('0.00'))

    def test_rejects_bad_percent(self):
        with self.assertRaises(ValueError):
            apply_discount('10.00', 101)

    def test_order_total(self):
        self.assertEqual(order_total([('a', 2, '1.50'), ('b', 1, '3.00')]), Decimal('6.00'))


if __name__ == '__main__':
    unittest.main()
