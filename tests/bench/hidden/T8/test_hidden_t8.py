import unittest

from inventory.stock import Stock


def reserved(levels, sku, quantity):
    stock = Stock(levels)
    stock.reserve(sku, quantity)
    return stock


class HiddenReleaseTest(unittest.TestCase):
    def test_release_more_than_reserved_is_rejected(self):
        stock = reserved({'a': 5}, 'a', 2)
        with self.assertRaises(ValueError):
            stock.release('a', 3)
        self.assertEqual(stock.reserved, {'a': 2})
        self.assertEqual(stock.available('a'), 3)

    def test_release_without_reservation_is_rejected(self):
        stock = reserved({'a': 5}, 'a', 2)
        with self.assertRaises(ValueError):
            stock.release('b', 1)
        self.assertEqual(stock.reserved, {'a': 2})

    def test_negative_release_does_not_grow_the_reservation(self):
        # The criterion: release only lowers the reservation. A negative quantity would raise it.
        stock = reserved({'a': 5}, 'a', 2)
        with self.assertRaises(ValueError):
            stock.release('a', -2)
        self.assertEqual(stock.reserved, {'a': 2})
        self.assertEqual(stock.available('a'), 3)

    def test_valid_release_still_works(self):
        stock = reserved({'a': 5}, 'a', 3)
        self.assertEqual(stock.release('a', 3), 5)
        self.assertEqual(stock.reserved.get('a', 0), 0)


if __name__ == '__main__':
    unittest.main()
