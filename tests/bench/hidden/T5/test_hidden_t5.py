import unittest
from decimal import Decimal

from inventory.shipping import shipping_cost


class HiddenShippingTest(unittest.TestCase):
    def test_started_kilogram_is_charged(self):
        self.assertEqual(shipping_cost(2.5), Decimal('7.30'))

    def test_light_parcel_pays_base_fee(self):
        self.assertEqual(shipping_cost('0.4'), Decimal('4.90'))

    def test_just_above_included_weight(self):
        self.assertEqual(shipping_cost('1.01'), Decimal('6.10'))

    def test_whole_kilograms_unchanged(self):
        self.assertEqual(shipping_cost(3), Decimal('7.30'))

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            shipping_cost(-1)
