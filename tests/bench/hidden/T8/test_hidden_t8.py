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



class HiddenReleaseManyTest(unittest.TestCase):
    """The second code path: a cancelled multi-line order must follow the same invariant, all or nothing."""

    def setUp(self):
        self.stock = Stock({'a': 5, 'b': 5})
        self.stock.reserve('a', 2)
        self.stock.reserve('b', 2)

    def assert_unchanged(self):
        self.assertEqual(self.stock.reserved, {'a': 2, 'b': 2})
        self.assertEqual((self.stock.available('a'), self.stock.available('b')), (3, 3))

    def test_over_release_on_a_later_line_changes_nothing(self):
        with self.assertRaises(ValueError):
            self.stock.release_many([('a', 1), ('b', 3)])
        self.assert_unchanged()

    def test_lines_with_the_same_sku_count_together(self):
        with self.assertRaises(ValueError):
            self.stock.release_many([('a', 2), ('a', 1)])
        self.assert_unchanged()

    def test_unknown_sku_changes_nothing(self):
        with self.assertRaises(ValueError):
            self.stock.release_many([('a', 1), ('c', 1)])
        self.assert_unchanged()

    def test_non_positive_line_changes_nothing(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                self.stock.release_many([('a', 1), ('b', bad)])
            self.assert_unchanged()

    def test_valid_release_many_still_works(self):
        self.assertEqual(self.stock.release_many([('a', 1), ('a', 1), ('b', 2)]), {'a': 5, 'b': 5})
        self.assertEqual(self.stock.reserved.get('a', 0) + self.stock.reserved.get('b', 0), 0)


if __name__ == '__main__':
    unittest.main()
