# import logging
# import os
# import re
# import sys
import warnings
from importlib.resources import files

import igraph as ig

import numpy as np

# import pandas as pd
import simplekml
from geopy.distance import great_circle

from .borders import *

SEA_EDGE_TYPES = ("sea", "sea_border")
BORDER_EDGE_TYPES = ("road_border", "sea_border")
ROAD_EDGE_TYPES = ("road", "road_sea")
OPEN_SEA_COUNTRY = "sea"

# Load the full graph
g = ig.load(files("traderoutes.assets").joinpath("fullgraph.pkl"), format="pickle")


def _clean_country(country):
    if country is None:
        return None
    if isinstance(country, str):
        country = country.strip()
        if country == "" or country == "None":
            return None
        return country
    if isinstance(country, float) and np.isnan(country):
        return None
    return country


def countries():
    """Return a sorted list of all countries present in the transportation network.

    A country is included if it has at least one city vertex (``vtype="city"``)
    in the graph.

    Returns:
        list[str]: Sorted list of ISO 3-letter country codes.

    Examples:
        >>> cs = countries()
        >>> "FRA" in cs
        True
    """
    return np.unique(g.vs.select(vtype="city")["country"]).tolist()


def get_main_city(country):
    """Return the main city vertex for a given country.

    The main city is the vertex with ``vtype="city"`` and ``maincity=1``
    for the specified country. It is used as the representative location for
    great-circle distance calculations and as the default path endpoint.

    Args:
        country (str): ISO 3-letter code of the country (e.g. ``"FRA"``).

    Returns:
        igraph.Vertex | None: The main city vertex, or ``None`` if not found.

    Warns:
        UserWarning: If no main city is found for the country.
        UserWarning: If more than one main city is found (returns the first).

    Examples:
        >>> v = get_main_city("FRA")
        >>> v["name"]
        'Paris'
    """
    mcs = g.vs.select(vtype="city", maincity=1, country=country)
    if len(mcs) == 0:
        warnings.warn(f"No main city found for country {country}.")
        return None
    elif len(mcs) > 1:
        warnings.warn(
            f"More than one main city found for country {country}. Return the first one."
        )
    return mcs[0]


def get_great_circle(country1, country2):
    """Return the great-circle distance in km between the main cities of two countries.

    Args:
        country1 (str): ISO 3-letter code of the origin country.
        country2 (str): ISO 3-letter code of the destination country.

    Returns:
        float: Great-circle distance in kilometres.

    Examples:
        >>> round(get_great_circle("FRA", "ITA"), 2)
        1109.56
    """
    city1 = get_main_city(country1)
    city2 = get_main_city(country2)
    return great_circle((city1["lat"], city1["lon"]), (city2["lat"], city2["lon"])).km


def get_trade_route_great_circle(country1, country2):
    """Return a dict with country codes and the great-circle distance between them.

    Args:
        country1 (str): ISO 3-letter code of the origin country.
        country2 (str): ISO 3-letter code of the destination country.

    Returns:
        dict: Dictionary with keys ``"iso_i"`` (origin), ``"iso_j"`` (destination),
            and ``"dist"`` (great-circle distance in km).

    Examples:
        >>> r = get_trade_route_great_circle("FRA", "ITA")
        >>> r["iso_i"], r["iso_j"]
        ('FRA', 'ITA')
    """
    return {
        "iso_i": country1,
        "iso_j": country2,
        "dist": get_great_circle(country1, country2),
    }


def get_path(
    v1,
    v2,
    road_cost=1,
    road_cost_countries={},
    port_cost=1,
    port_cost_countries={},
    border_cost=0,
    border_cost_countries={},
):
    """Return the shortest-path trade route between two graph vertices.

    The returned path corresponds to the shortest path weighted by the costs
    applied to the graph edges, as determined by the arguments.

    Cost application order:

    1. All edges are initialized to their true distance (``wdist = dist``).
    2. **Port edges** (``etype="road_sea"``): ``wdist = dist + port_cost``.
       Per-country overrides in *port_cost_countries* take precedence.
    3. **Border edges** (``etype`` in ``("road_border", "sea_border")``):
       ``wdist = dist + border_cost``. Per-pair overrides in
       *border_cost_countries* take precedence.
    4. **Road edges** (``etype="road"``): ``wdist = dist * road_cost``.
       Per-country overrides in *road_cost_countries* take precedence.

    Args:
        v1: Source vertex (igraph Vertex object).
        v2: Destination vertex (igraph Vertex object).
        road_cost (float): Multiplicative cost factor for road edges.
            Applies to all road edges not listed in *road_cost_countries*,
            excluding cross-border road edges. Default: ``1``.
        road_cost_countries (dict[str, float]): Per-country road cost overrides.
            Keys are ISO3 codes; values replace the global *road_cost* for
            road edges fully inside that country. Example: ``{"FRA": 2}``.
        port_cost (float): Additive cost for land-to-sea transitions
            (``road_sea`` edges). Default: ``1``.
        port_cost_countries (dict[str, float]): Per-country port cost overrides.
            Keys are ISO3 codes. Example: ``{"FRA": 2}``.
        border_cost (float): Additive cost for crossing a country border
            (``road_border`` and ``sea_border`` edges). Default: ``0``.
        border_cost_countries (dict[tuple[str, str], float]): Per-country-pair
            border cost overrides. Keys are tuples of ISO3 codes.
            Example: ``{("FRA", "DEU"): 500}``.

    Returns:
        dict: Dictionary with two keys:

            - ``"epath"`` (list[int]): Edge indices of the shortest path.
            - ``"vpath"`` (list[int]): Vertex indices of the shortest path.

    Examples:
        >>> v_fra = get_main_city("FRA")
        >>> v_nld = get_main_city("NLD")
        >>> path = get_path(v_fra, v_nld, road_cost=7, port_cost=1e4)
        >>> get_pattern(path)
        'crc'
    """
    # 0. Initialize all weighted distance at actual distance
    g.es["wdist"] = g.es["dist"]
    # 1. Apply port costs
    ports = g.es.select(etype="road_sea")
    ports["wdist"] = (np.array(ports["dist"]) + port_cost).tolist()
    for c in port_cost_countries:
        ports_c = ports.select(country=c)
        country_port_cost = port_cost_countries[c]
        ports_c["wdist"] = (np.array(ports_c["dist"]) + country_port_cost).tolist()
    # 2. Apply border costs
    borders = g.es.select(etype_in=BORDER_EDGE_TYPES)
    borders["wdist"] = (np.array(borders["dist"]) + border_cost).tolist()
    for cs in border_cost_countries:
        borders_c = borders.select(country1_in=cs, country2_in=cs)
        country_border_cost = border_cost_countries[cs]
        borders_c["wdist"] = (
            np.array(borders_c["dist"]) + country_border_cost
        ).tolist()
    # 3. Apply road costs
    roads = g.es.select(etype="road")
    roads["wdist"] = (np.array(roads["dist"]) * road_cost).tolist()
    for c in road_cost_countries:
        roads_c = roads.select(country=c)
        country_road_cost = road_cost_countries[c]
        roads_c["wdist"] = (np.array(roads_c["dist"]) * country_road_cost).tolist()

    # Compute shortest path
    epath = g.get_shortest_paths(v1, v2, weights="wdist", output="epath")[0]
    vpath = g.get_shortest_paths(v1, v2, weights="wdist", output="vpath")[0]

    return {"epath": epath, "vpath": vpath}


def get_pattern(path):
    """Return a string encoding the sequence of vertex types along a path.

    The pattern compresses consecutive vertices of the same type into a single
    character: ``c`` = city, ``r`` = road, ``p`` = port, ``s`` = sea.
    Intermediate city vertices (i.e. not the first or last vertex) are treated
    as road vertices so they do not break the road segment pattern.

    Args:
        path (dict): Path dict as returned by :func:`get_path`, with key
            ``"vpath"`` containing vertex indices.

    Returns:
        str: Pattern string, e.g. ``"crc"`` (land route), ``"csrc"``
            (sea route with sea from origin side).

    Examples:
        >>> path = get_path(get_main_city("FRA"), get_main_city("DEU"), road_cost=7)
        >>> get_pattern(path)
        'crc'
    """
    vpath = path["vpath"]
    vtypes = [g.vs.select(vpath)[0]["vtype"]]
    for v in g.vs.select(vpath)[1:-1]:
        vtype = v["vtype"]
        if vtype == "city":
            vtype = "road"
        if vtype != vtypes[-1]:
            vtypes.append(vtype)
    vtypes.append(g.vs.select(vpath)[-1]["vtype"])

    return "".join(
        list(map({"city": "c", "port": "p", "road": "r", "sea": "s"}.get, vtypes))
    )


def get_countries(path, with_sea=False, clean_dist=None):
    """Return the sequence of countries traversed along a path.

    Each entry in the returned list is a ``(country, distance)`` tuple, where
    *distance* is the total distance (km) traveled within that country segment.

    Args:
        path (dict): Path dict as returned by :func:`get_path`.
        with_sea (bool): If ``True``, sea segments are included as entries with
            country code ``"sea"``. Default: ``False``.
        clean_dist (float | None): If set, iteratively removes intermediate
            countries whose segment distance is below *clean_dist* km, until
            all remaining intermediate segments are at or above the threshold
            (or only the origin and destination remain). Default: ``None``.

    Returns:
        list[tuple[str, float]]: List of ``(country_iso3, distance_km)`` tuples
            in traversal order. Sea segments appear as ``("sea", distance)`` when
            *with_sea* is ``True``.

    Examples:
        >>> path = get_path(get_main_city("FRA"), get_main_city("POL"), road_cost=7)
        >>> [c for c, _ in get_countries(path)]
        ['FRA', 'DEU', 'POL']
    """
    vpath = path["vpath"]
    countries = []
    vs = g.vs.select(vpath)
    c = _clean_country(vs[0]["country"])
    d = 0
    for i in range(1, len(vs)):
        d += g.es.select(_source=vpath[i - 1], _target=vpath[i])[0]["dist"]
        next_c = _clean_country(vs[i]["country"])
        if next_c != c:
            segment_country = OPEN_SEA_COUNTRY if c is None and with_sea else c
            if segment_country is not None:
                countries += [(segment_country, d)]
            c = next_c
            d = 0
    segment_country = OPEN_SEA_COUNTRY if c is None and with_sea else c
    if segment_country is not None:
        countries += [(segment_country, d)]
    if clean_dist is not None:
        cleaned = False
        while not cleaned and len(countries) > 2:
            dists = [c[1] for c in countries]
            min_d = min(dists[1:-1])
            if min_d < clean_dist:
                countries = [
                    countries[i]
                    for i in range(0, len(countries))
                    if i != dists.index(min_d)
                ]
                # Consolidate consecutive same-country segments
                countries_new = []
                cd = countries[0]
                for i in range(1, len(countries)):
                    if countries[i][0] == cd[0]:
                        cd = (cd[0], cd[1] + countries[i][1])
                    else:
                        countries_new += [cd]
                        cd = countries[i]
                countries_new += [cd]
                countries = countries_new
            else:
                cleaned = True

    return countries


def road_distance(path):
    """Return the total road distance (km) along a path.

    Sums the ``dist`` attribute of all edges with ``etype`` in
    ``("road", "road_sea")``.

    Args:
        path (dict): Path dict as returned by :func:`get_path`.

    Returns:
        float: Total road distance in kilometres.
    """
    roads = g.es.select(path["epath"]).select(etype_in=ROAD_EDGE_TYPES)
    return sum(roads["dist"])


def sea_distance(path):
    """Return the total sea distance (km) along a path.

    Sums the ``dist`` attribute of all edges with ``etype`` in
    ``("sea", "sea_border")``.

    Args:
        path (dict): Path dict as returned by :func:`get_path`.

    Returns:
        float: Total sea distance in kilometres.
    """
    seas = g.es.select(path["epath"]).select(etype_in=SEA_EDGE_TYPES)
    return sum(seas["dist"])


def transits_i(path, clean_dist=None):
    """Return transit country ISO3 codes from the origin side of a path.

    For **land-only** routes (no sea segment): all intermediate countries
    between origin and destination are returned.

    For routes **with sea**: only countries between the origin and the first
    sea segment are returned.

    Args:
        path (dict): Path dict as returned by :func:`get_path`.
        clean_dist (float | None): Passed to :func:`get_countries` to remove
            very short country segments. Default: ``None``.

    Returns:
        list[str]: ISO3 codes of transit countries on the origin side,
            in traversal order.

    Raises:
        Exception: If the sea is used more than once in the path.

    Examples:
        >>> path = get_path(get_main_city("CHE"), get_main_city("POL"), road_cost=7)
        >>> transits_i(path)  # Switzerland → (DEU or AUT) → Poland
        ['DEU']
    """
    pattern = get_pattern(path)
    if "s" not in pattern:
        cs = [c[0] for c in get_countries(path, clean_dist=clean_dist)]
        return cs[1:-1]
    else:
        if pattern.count("s") > 1:
            raise Exception(
                f"Cannot compute transit countries for pattern '{pattern}' because sea is used more than once."
            )
        cs = [c[0] for c in get_countries(path, with_sea=True, clean_dist=clean_dist)]
        if OPEN_SEA_COUNTRY not in cs:
            return cs[1:-1]
        return cs[1 : cs.index(OPEN_SEA_COUNTRY)]


def transits_j(path, clean_dist=None):
    """Return transit country ISO3 codes from the destination side of a path.

    Equivalent to :func:`transits_i` applied to the reversed path, identifying
    countries between the destination and the last sea segment (or all
    intermediate countries for land-only routes).

    Args:
        path (dict): Path dict as returned by :func:`get_path`.
        clean_dist (float | None): Passed to :func:`get_countries` to remove
            very short country segments. Default: ``None``.

    Returns:
        list[str]: ISO3 codes of transit countries on the destination side,
            in reverse traversal order (i.e. destination-outward).

    Raises:
        Exception: If the sea is used more than once in the path.
    """
    path_reversed = {
        "vpath": list(reversed(path["vpath"])),
        "epath": list(reversed(path["epath"])),
    }
    return transits_i(path_reversed, clean_dist=clean_dist)


######################
# Plotting Functions #
######################


def to_kml(path, filename):
    """Export a trade route path to a KML file for viewing in Google Earth.

    The path is drawn as a red line connecting consecutive vertices.

    Args:
        path (dict): Path dict as returned by :func:`get_path`.
        filename (str): Output file path (e.g. ``"route.kml"``).

    Examples:
        >>> path = get_path(get_main_city("FRA"), get_main_city("NLD"), road_cost=7)
        >>> to_kml(path, "fra_nld.kml")
    """
    vpath = path["vpath"]
    kml = simplekml.Kml()
    coord0 = (g.vs[vpath[0]]["lon"], g.vs[vpath[0]]["lat"])
    for i in range(1, len(vpath)):
        coord1 = (g.vs[vpath[i]]["lon"], g.vs[vpath[i]]["lat"])
        ls = kml.newlinestring(coords=[coord0, coord1])
        ls.style.linestyle.width = 5
        ls.style.linestyle.color = simplekml.Color.red
        coord0 = coord1
    kml.save(filename)


def cities_to_kml(filename, all_cities=False):
    """Export city locations to a KML file, organised by country folder.

    Args:
        filename (str): Output file path.
        all_cities (bool): If ``False`` (default), only main cities are exported.
            If ``True``, all city vertices are exported.
    """
    kml = simplekml.Kml()
    if all_cities:
        cities = g.vs.select(vtype="city")
    else:
        cities = g.vs.select(vtype="city", maincity=True)

    for co in countries():
        fc = kml.newfolder(name=co)
        for c in cities.select(country=co):
            coord = (c["lon"], c["lat"])
            pt = kml.newpoint(name=f"{c['name']} - {c['country']}", coords=[coord])
            pt.style.iconstyle.color = simplekml.Color.yellow
    kml.save(filename)


def ports_to_kml(filename):
    """Export port locations to a KML file, organised by country folder.

    Args:
        filename (str): Output file path.
    """
    kml = simplekml.Kml()
    ports = g.vs.select(vtype="port")
    for c in countries():
        fc = kml.newfolder(name=c)
        for p in ports.select(country=c):
            coord = (p["lon"], p["lat"])
            pt = fc.newpoint(name=f"{p['name']} - {p['country']}", coords=[coord])
            pt.style.iconstyle.color = simplekml.Color.aqua
    kml.save(filename)


def roads_to_kml(filename):
    """Export the road network to a KMZ file, organised by country folder.

    Args:
        filename (str): Output file path (without extension; ``.kmz`` is appended).
    """
    kml = simplekml.Kml()
    edges = g.es.select(etype_in=ROAD_EDGE_TYPES)
    road_countries = np.unique(g.vs.select(vtype="road")["country"])

    for c in road_countries.tolist() + [None]:
        print(c, end="\r")
        es = edges.select(country=c)
        fc = kml.newfolder(name=c)
        for e in es:
            coords_source = (g.vs[e.source]["lon"], g.vs[e.source]["lat"])
            coords_target = (g.vs[e.target]["lon"], g.vs[e.target]["lat"])
            ls = fc.newlinestring(coords=[coords_source, coords_target])
            ls.style.linestyle.width = 1
            ls.style.linestyle.color = simplekml.Color.yellow

    print("Save file")
    kml.savekmz(f"{filename}.kmz", format=False)


def seas_to_kml(filename):
    """Export the sea-lane network, including sea-border edges, to a KMZ file.

    Args:
        filename (str): Output file path (without extension; ``.kmz`` is appended).
    """
    kml = simplekml.Kml()
    edges = g.es.select(etype_in=SEA_EDGE_TYPES)

    for e in edges:
        coords_source = (g.vs[e.source]["lon"], g.vs[e.source]["lat"])
        coords_target = (g.vs[e.target]["lon"], g.vs[e.target]["lat"])
        ls = kml.newlinestring(coords=[coords_source, coords_target])
        ls.style.linestyle.width = 1
        ls.style.linestyle.color = simplekml.Color.cyan

    kml.savekmz(f"{filename}.kmz", format=False)
