import unittest

from inventory.stock import Stock


class StockTest(unittest.TestCase):
    def test_reserve_and_ship(self):
        stock = Stock({'a': 5})
        self.assertEqual(stock.reserve('a', 2), 3)
        stock.ship('a', 2)
        self.assertEqual(stock.levels['a'], 3)

    def test_restock_returned(self):
        stock = Stock({'a': 1})
        stock.restock_returned('a', 2)
        self.assertEqual(stock.available('a'), 3)


if __name__ == '__main__':
    unittest.main()
