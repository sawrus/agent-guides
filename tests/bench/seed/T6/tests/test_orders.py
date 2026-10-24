import unittest
from decimal import Decimal

from inventory.orders import Order


class OrderTest(unittest.TestCase):
    def test_invoice_without_discount(self):
        order = Order()
        order.add('a', 2, '5.00')
        invoice = order.invoice(tax_percent=10)
        self.assertEqual(invoice['tax'], Decimal('1.00'))
        self.assertEqual(invoice['total'], Decimal('11.00'))

    def test_rejects_empty_line(self):
        with self.assertRaises(ValueError):
            Order().add('a', 0, '1.00')


if __name__ == '__main__':
    unittest.main()
