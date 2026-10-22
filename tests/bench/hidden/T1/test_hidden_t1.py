import unittest
from decimal import Decimal

from inventory.pricing import apply_discount, order_total


class HiddenDiscountTest(unittest.TestCase):
    def test_issue_example(self):
        self.assertEqual(apply_discount('19.99', 15), Decimal('16.99'))

    def test_small_amount(self):
        self.assertEqual(apply_discount('0.10', 50), Decimal('0.05'))

    def test_discount_rounds_half_up_to_cents(self):
        self.assertEqual(apply_discount('33.33', 10), Decimal('30.00'))

    def test_order_total_uses_fixed_discount(self):
        self.assertEqual(order_total([('a', 1, '19.99')], 15), Decimal('16.99'))
