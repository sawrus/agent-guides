import io
import unittest
from contextlib import redirect_stdout
from decimal import Decimal

from inventory import cli
from inventory.pricing import split_payment


class HiddenSplitTest(unittest.TestCase):
    def test_remainder_goes_to_first_parts(self):
        expected = [Decimal('3.34'), Decimal('3.33'), Decimal('3.33')]
        self.assertEqual(split_payment('10.00', 3), expected)

    def test_parts_sum_to_total(self):
        self.assertEqual(sum(split_payment('100.01', 7)), Decimal('100.01'))

    def test_single_part(self):
        self.assertEqual(split_payment('5', 1), [Decimal('5.00')])

    def test_rejects_less_than_one_part(self):
        with self.assertRaises(ValueError):
            split_payment('10.00', 0)

    def test_cli_prints_one_part_per_line(self):
        out = io.StringIO()
        with redirect_stdout(out):
            cli.main(['split', '10.00', '3'])
        self.assertEqual(out.getvalue().split(), ['3.34', '3.33', '3.33'])
