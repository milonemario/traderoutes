import unittest
import warnings

import numpy as np

from traderoutes.routes import *


class TestRoutes(unittest.TestCase):
    def _trade_path(self, country1, country2, border_cost=0, border_cost_countries=None):
        if border_cost_countries is None:
            border_cost_countries = {}
        return get_path(
            get_main_city(country1),
            get_main_city(country2),
            road_cost=7,
            port_cost=1e4,
            port_cost_countries={country1: 5e3, country2: 5e3},
            border_cost=border_cost,
            border_cost_countries=border_cost_countries,
        )

    def test_get_main_city(self):
        # Check only one main city per country
        countries = np.unique(g.vs.select(vtype="city")["country"])
        with warnings.catch_warnings(record=True) as warnings_log:
            warnings.simplefilter("always")
            for c in countries:
                mc = get_main_city(c)
            self.assertEqual(
                len(warnings_log),
                0,
                f"Unexpected warnings: {[w.message for w in warnings_log]}",
            )

    def test_get_great_circle(self):
        self.assertAlmostEqual(get_great_circle("FRA", "ITA"), 1109.56, places=2)

    def test_get_trade_route_great_circle(self):
        tr = get_trade_route_great_circle("FRA", "ITA")
        self.assertEqual(tr["iso_i"], "FRA")
        self.assertEqual(tr["iso_j"], "ITA")
        self.assertAlmostEqual(tr["dist"], 1109.56, places=2)

    def test_sea_distance_includes_sea_border(self):
        path = self._trade_path("PRY", "USA")
        edges = g.es.select(path["epath"])
        self.assertIn("sea_border", edges["etype"])

        expected = sum(e["dist"] for e in edges if e["etype"] in SEA_EDGE_TYPES)
        self.assertAlmostEqual(sea_distance(path), expected)

    def test_paraguay_usa_origin_transits(self):
        path = self._trade_path("PRY", "USA")
        ti = transits_i(path)
        tj = transits_j(path)

        self.assertGreater(len(ti), 0)
        self.assertIn("ARG", ti)
        self.assertNotIn("PRY", ti + tj)
        self.assertNotIn("USA", ti + tj)

    def test_sea_border_country_pair_costs(self):
        self._trade_path(
            "PRY",
            "USA",
            border_cost=1e4,
            border_cost_countries={("ARG", "PRY"): 5e4},
        )
        edges = g.es.select(
            etype="sea_border", country1_in=("ARG", "PRY"), country2_in=("ARG", "PRY")
        )

        self.assertGreater(len(edges), 0)
        for edge in edges:
            self.assertAlmostEqual(edge["wdist"], edge["dist"] + 5e4)


if __name__ == "__main":
    unittest.main()
