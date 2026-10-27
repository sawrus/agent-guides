import unittest

from inventory.stock import Stock


class ReleaseTest(unittest.TestCase):
    def test_release_part_of_reservation(self):
        stock = Stock({'a': 5})
        stock.reserve('a', 3)
        self.assertEqual(stock.release('a', 2), 4)
        self.assertEqual(stock.reserved['a'], 1)

    def test_release_whole_reservation(self):
        stock = Stock({'a': 5})
        stock.reserve('a', 2)
        self.assertEqual(stock.release('a', 2), 5)

    def test_release_many_lines(self):
        stock = Stock({'a': 5, 'b': 4})
        stock.reserve('a', 3)
        stock.reserve('b', 2)
        self.assertEqual(stock.release_many([('a', 1), ('b', 2)]), {'a': 3, 'b': 4})


if __name__ == '__main__':
    unittest.main()
