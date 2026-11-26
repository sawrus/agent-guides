import unittest

from wordfreq import top


class TopTest(unittest.TestCase):
    def test_order_and_case(self):
        self.assertEqual(top('b A a B c', 2), [('a', 2), ('b', 2)])

    def test_empty(self):
        self.assertEqual(top('', 3), [])

    def test_limit(self):
        self.assertEqual(len(top('a b c d', 2)), 2)
