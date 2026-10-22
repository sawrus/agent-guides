import unittest
from decimal import Decimal

from inventory.shipping import shipping_cost


class ShippingTest(unittest.TestCase):
    def test_first_kilogram_is_base_fee(self):
        self.assertEqual(shipping_cost(1), Decimal('4.90'))

    def test_whole_kilograms(self):
        self.assertEqual(shipping_cost(3), Decimal('7.30'))

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            shipping_cost(0)
