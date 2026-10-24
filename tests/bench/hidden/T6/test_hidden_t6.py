import unittest
from decimal import Decimal

from inventory.orders import Order
from inventory.pricing import apply_discount


def order(*lines):
    result = Order()
    for sku, quantity, price in lines:
        result.add(sku, quantity, price)
    return result


class HiddenInvoiceTest(unittest.TestCase):
    def test_issue_example(self):
        invoice = order(('a', 3, '19.99')).invoice(15, 20)
        self.assertEqual(invoice['discounted'], Decimal('50.97'))
        self.assertEqual(invoice['tax'], Decimal('10.19'))
        self.assertEqual(invoice['total'], Decimal('61.16'))

    def test_tax_uses_discounted_amount(self):
        invoice = order(('a', 1, '100.00')).invoice(10, 10)
        self.assertEqual(invoice['tax'], Decimal('9.00'))
        self.assertEqual(invoice['total'], Decimal('99.00'))

    def test_discount_rounds_to_cents(self):
        self.assertEqual(apply_discount('0.10', 50), Decimal('0.05'))
        self.assertEqual(order(('a', 1, '0.10')).invoice(50, 0)['total'], Decimal('0.05'))

    def test_no_discount_no_tax(self):
        invoice = order(('a', 2, '1.50'), ('b', 1, '3.00')).invoice()
        self.assertEqual(invoice['total'], Decimal('6.00'))
