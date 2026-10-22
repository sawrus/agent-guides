import unittest

from inventory.stock import OutOfStock, Stock


class HiddenReserveTest(unittest.TestCase):
    def test_over_reservation_raises(self):
        stock = Stock({'a': 2})
        with self.assertRaises(OutOfStock):
            stock.reserve('a', 3)

    def test_failed_reservation_keeps_state(self):
        stock = Stock({'a': 2})
        stock.reserve('a', 1)
        with self.assertRaises(OutOfStock):
            stock.reserve('a', 2)
        self.assertEqual(stock.available('a'), 1)

    def test_exact_reservation_allowed(self):
        stock = Stock({'a': 2})
        self.assertEqual(stock.reserve('a', 2), 0)

    def test_unknown_sku_is_out_of_stock(self):
        with self.assertRaises(OutOfStock):
            Stock().reserve('b', 1)
