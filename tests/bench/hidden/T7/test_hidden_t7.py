import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from inventory import cli
from inventory.stock import OutOfStock, Stock


class HiddenReserveManyTest(unittest.TestCase):
    def test_reserves_every_line(self):
        stock = Stock({'a': 5, 'b': 2})
        self.assertEqual(stock.reserve_many([('a', 3), ('b', 1)]), {'a': 2, 'b': 1})
        self.assertEqual(stock.available('a'), 2)

    def test_all_or_nothing(self):
        stock = Stock({'a': 5, 'b': 1})
        with self.assertRaises(OutOfStock):
            stock.reserve_many([('a', 2), ('b', 2)])
        self.assertEqual((stock.available('a'), stock.available('b')), (5, 1))

    def test_same_sku_lines_count_together(self):
        stock = Stock({'a': 5})
        with self.assertRaises(OutOfStock):
            stock.reserve_many([('a', 3), ('a', 3)])
        self.assertEqual(stock.available('a'), 5)

    def test_bad_quantity_keeps_state(self):
        stock = Stock({'a': 5})
        with self.assertRaises(ValueError):
            stock.reserve_many([('a', 1), ('a', 0)])
        self.assertEqual(stock.available('a'), 5)

    def test_cli_prints_remaining_per_sku(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(['reserve', '--stock', 'B:2,A:5', 'B:1', 'A:3'])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().splitlines(), ['A 2', 'B 1'])

    def test_cli_out_of_stock_exit_code(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(['reserve', '--stock', 'A:1', 'A:2'])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertTrue(err.getvalue().strip())
