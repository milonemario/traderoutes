import unittest

from traderoutes.borders import *


class TestBorders(unittest.TestCase):

    def test_get_neighbors(self):
        self.assertEqual(get_neighbors("USA"), ["MEX", "CAN"])

    def test_are_neighbors(self):
        self.assertEqual(are_neighbors("FRA", "ITA"), True)
        self.assertEqual(are_neighbors("FRA", "USA"), False)

    def test_get_second_neighbors(self):
        self.assertEqual(
            get_second_neighbors("FRA"),
            [
                "MAR",
                "PRT",
                "AUT",
                "CZE",
                "POL",
                "NLD",
                "DNK",
                "SVN",
                "SMR",
                "VAT",
                "LIE",
            ],
        )

    def test_get_common_neighbors(self):
        self.assertEqual(get_common_neighbors("FRA", "ITA"), ["CHE"])


if __name__ == "__main":
    unittest.main()
