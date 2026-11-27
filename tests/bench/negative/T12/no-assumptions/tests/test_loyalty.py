import unittest
from decimal import Decimal

from inventory.pricing import loyalty_price


class LoyaltyTest(unittest.TestCase):
    def test_steps_and_cap(self):
        self.assertEqual(loyalty_price('100.00', 4), Decimal('100.00'))
        self.assertEqual(loyalty_price('100.00', 5), Decimal('98.00'))
        self.assertEqual(loyalty_price('100.00', 500), Decimal('80.00'))
