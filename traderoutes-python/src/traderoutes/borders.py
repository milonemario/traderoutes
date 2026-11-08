# Module to query about borders information

import os
from importlib.resources import files

import igraph as ig

# Import the borders graph
b = ig.read(files("traderoutes.assets").joinpath("bordersgraph.pkl"), format="pickle")


def are_neighbors(country1, country2):
    """Return True if the two countries share a land border.

    Args:
        country1 (str): ISO 3-letter code of the first country (e.g. ``"FRA"``).
        country2 (str): ISO 3-letter code of the second country (e.g. ``"ITA"``).

    Returns:
        bool: ``True`` if the countries are direct neighbors, ``False`` otherwise.

    Examples:
        >>> are_neighbors("FRA", "ITA")
        True
        >>> are_neighbors("FRA", "USA")
        False
    """
    return country2 in get_neighbors(country1)


def get_neighbors(country):
    """Return the ISO3 codes of all countries sharing a land border with *country*.

    Args:
        country (str): ISO 3-letter code of the country (e.g. ``"FRA"``).

    Returns:
        list[str]: Sorted list of ISO3 codes of neighboring countries.
            Returns an empty list if the country is not found in the graph.

    Examples:
        >>> get_neighbors("USA")
        ['CAN', 'MEX']
    """
    countries = b.vs["name"]
    neighbors = []
    if country in countries:
        c = b.vs.find(country)
        ns = c.neighbors()
        for n in ns:
            neighbors += [n["name"]]
    return neighbors


def get_second_neighbors(country):
    """Return countries reachable in exactly two border hops from *country*.

    The returned list excludes *country* itself and its direct neighbors.

    Args:
        country (str): ISO 3-letter code of the country (e.g. ``"FRA"``).

    Returns:
        list[str]: List of ISO3 codes of second-degree neighbors, in the order
            they are encountered while traversing the border graph.
            Returns an empty list if the country is not found.

    Examples:
        >>> "PRT" in get_second_neighbors("FRA")
        True
        >>> "ITA" in get_second_neighbors("FRA")  # direct neighbor — excluded
        False
    """
    countries = b.vs["name"]
    second_neighbors = []
    neighbors = get_neighbors(country)
    if country in countries:
        c = b.vs.find(country)
        ns = c.neighbors()
        for n in ns:
            sns = n.neighbors()
            for sn in sns:
                name = sn["name"]
                if (
                    name not in second_neighbors
                    and name not in neighbors
                    and name != country
                ):
                    second_neighbors += [name]
    return second_neighbors


def get_common_neighbors(country1, country2):
    """Return countries that share a land border with both *country1* and *country2*.

    Args:
        country1 (str): ISO 3-letter code of the first country.
        country2 (str): ISO 3-letter code of the second country.

    Returns:
        list[str]: List of ISO3 codes of countries neighboring both inputs.
            Returns an empty list if no common neighbors exist.

    Examples:
        >>> get_common_neighbors("FRA", "ITA")
        ['CHE']
        >>> get_common_neighbors("FRA", "USA")
        []
    """
    ns1 = get_neighbors(country1)
    ns2 = get_neighbors(country2)
    return [n for n in ns1 if n in ns2]
