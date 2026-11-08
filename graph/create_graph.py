# Python script to create the final graph to compute routes

import gc
import os
import sys
import warnings
from typing import List

import geopandas as gp
import igraph as ig
import momepy
import networkx as nx
import numpy as np
import pandas as pd
import scipy
import shapely
from geopy.distance import great_circle
from shapely import LineString, Point
from shapely.wkt import loads


# Convert Shapefiles to igraph format
def read_shapefile_old(file):
    # Load the shapefile
    gdf = gp.read_file(file)
    graphnx = momepy.gdf_to_nx(gdf.explode(), approach="primal")
    return ig.Graph.from_networkx(graphnx)


def write_shapefile(g, file, geometry="points"):
    if geometry == "points":
        df = pd.DataFrame(
            {a: g.vs[a] for a in g.vs.attributes() if a not in ["lat", "lon"]}
        )
        gdf = gp.GeoDataFrame(df, geometry=gp.points_from_xy(g.vs["lon"], g.vs["lat"]))
        gdf.to_file(file)
    elif geometry == "lines":
        print("Create edges (may take some time)")
        df = pd.DataFrame({a: g.es[a] for a in g.es.attributes()})
        esl = [
            shapely.LineString(
                [
                    [g.vs[e.source]["lon"], g.vs[e.source]["lat"]],
                    [g.vs[e.target]["lon"], g.vs[e.target]["lat"]],
                ]
            )
            for e in g.es
        ]
        gdf = gp.GeoDataFrame(df, geometry=esl)
        gdf.to_file(file)


def haversine(lon1, lat1, lon2, lat2, comb=False, sparse=False):
    # lon1, lat1, lon2, lat2 = np.radians([lon1, lat1, lon2, lat2])
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    if comb:
        # lon1 = np.expand_dims(lon1, 0)
        # lat1 = np.expand_dims(lat1, 0)
        # lon2 = np.expand_dims(lon2, 1)
        # lat2 = np.expand_dims(lat2, 1)
        # Note: lon2/lat2 are the rows, lon1/lat1 are the columns
        lon1, lon2 = np.meshgrid(lon1, lon2, sparse=True)
        lat1, lat2 = np.meshgrid(lat1, lat2, sparse=True)

    r = 6371  # 6371 for distance in KM for miles use 3958.756

    if sparse:
        # Note: if sparse, comb==True
        mask = (abs(lon2 - lon1) < 0.01) & (abs(lat2 - lat1) < 0.01)
        mask_i = np.where(mask)
        # Use sparse matrices
        # Note: mask_i[0] is the first dimension (lon2/lat2)
        lon2_f = lon2[mask_i[0], 0]
        lat2_f = lat2[mask_i[0], 0]
        lon1_f = lon1[0, mask_i[1]]
        lat1_f = lat1[0, mask_i[1]]

        dlon_f = lon2_f - lon1_f
        dlat_f = lat2_f - lat1_f

        haver_formula = (
            np.sin(dlat_f / 2) ** 2
            + np.cos(lat1_f) * np.cos(lat2_f) * np.sin(dlon_f / 2) ** 2
        )

        dist_f = 2 * r * np.arcsin(np.sqrt(haver_formula))

        # Create sparse matrix
        dist = scipy.sparse.csr_matrix(
            (dist_f, (mask_i[0], mask_i[1])), shape=(lon2.shape[0], lon1.shape[1])
        )

        # s1 = lon1.shape[1]
        # s2 = lon2.shape[0]
        # lon1 = np.repeat(lon1, s2, 0)
        # lat1 = np.repeat(lat1, s2, 0)
        # lon2 = np.repeat(lon2, s1, 1)
        # lat2 = np.repeat(lat2, s1, 1)
        # mask = (dlon < 0.01) & (dlat < 0.01)
        # dist = 1e10 + np.zeros(dlon.shape)
        # dist = sparse.csr_matrix((dlon.shape))
        # haver_formula = (
        #     np.sin(dlat[mask] / 2) ** 2
        #     + np.cos(lat1[mask]) * np.cos(lat2[mask]) * np.sin(dlon[mask] / 2) ** 2
        # )
        # dist[mask] = 2 * r * np.arcsin(np.sqrt(haver_formula))
    else:
        dlon = abs(lon2 - lon1)
        dlat = abs(lat2 - lat1)
        haver_formula = (
            np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        )
        dist = 2 * r * np.arcsin(np.sqrt(haver_formula))

    return dist


def compute_distances_old(g):
    # Compute distances for a given graph
    for e in g.es:
        e["dist"] = great_circle(
            (g.vs[e.source]["lat"], g.vs[e.source]["lon"]),
            (g.vs[e.target]["lat"], g.vs[e.target]["lon"]),
        ).km


def merge_vertices(g, inds):
    # Merge vertices with exact same lon/lat for graph g for indices inds

    vs = g.vs[inds]

    lon1, lon2 = np.meshgrid(vs["lon"], vs["lon"], sparse=True)
    lat1, lat2 = np.meshgrid(vs["lat"], vs["lat"], sparse=True)
    mask = (lon2 == lon1) & (lat2 == lat1)
    mask_i = np.where(mask)

    # Note: mask_i[0] is the first dimension (lon2/lat2)
    # Indices for same location but different vertices
    mask2 = mask_i[0][mask_i[0] != mask_i[1]]
    mask1 = mask_i[1][mask_i[0] != mask_i[1]]
    # Convert to full graph indices
    inds_fg = np.array(vs.indices)
    mask2_fg = inds_fg[mask2]
    mask1_fg = inds_fg[mask1]
    # (mask1[i], mask2[i]) gives indices pairs with same location
    # Need to make groups
    # Find all similar indices from mask1 and group them with mask2 indices
    # Create the mapping over the full graph directly
    # Doing it the other way around gives the same mapping
    groups = []
    assigned = []
    mapping = np.array(g.vs.indices)
    for i1 in np.unique(mask1_fg):
        if i1 not in assigned:
            gr = mask2_fg[mask1_fg == i1]
            if len(gr) > 0:
                mapping[gr] = i1
                groups += [[int(i1)] + gr.tolist()]
                assigned += gr.tolist()

    # Merge vertices
    # Create the mapping (over the full graph)
    g.contract_vertices(mapping, combine_attrs="first")
    # Remove dropped vertices
    inds_toremove = g.vs.select(_degree=0).indices
    g.delete_vertices(inds_toremove)


def __add_distance(g, edges):
    # Add the distance attribute to the list of edges
    None


def __connect_close_vertices(g, inds1, inds2, max_km=5, single_connection=False):
    # Try to connect vertices ind1 to vertices inds2
    vs1 = g.vs[inds1]
    vs2 = g.vs[inds2]

    if len(vs2) > 0:

        lon1, lon2 = np.meshgrid(vs1["lon"], vs2["lon"], sparse=True)
        lat1, lat2 = np.meshgrid(vs1["lat"], vs2["lat"], sparse=True)
        # Note: 1 degree lat/lon is approximately 111km
        mask = (
            (abs(lon2 - lon1) > 0)
            & (abs(lon2 - lon1) < max_km / 100)
            & (abs(lat2 - lat1) > 0)
            & (abs(lat2 - lat1) < max_km / 100)
        )
        mask_i = np.where(mask)

        if len(mask_i[0]) > 0:
            # Note: mask_i[0] is the first dimension (lon2/lat2)
            # Indices for closed locations but different vertices
            mask2 = mask_i[0]
            mask1 = mask_i[1]
            # Convert to full graph indices
            inds1_fg = np.array(inds1)
            inds2_fg = np.array(inds2)
            inds2 = inds2_fg[mask2]
            inds1 = inds1_fg[mask1]

            # Do not consider edges that already exist
            # Get all the current existing edges between these vertices
            # inds1, inds2 = zip(*edges)
            ces = g.es.select(_between=(inds1, inds2))
            c_edges = list(zip([e.source for e in ces], [e.target for e in ces]))
            c_edges += list(zip([e.target for e in ces], [e.source for e in ces]))
            edges = list(zip(inds1.tolist(), inds2.tolist()))
            edges_toadd = list(set(edges) - set(c_edges))
            if len(edges_toadd) > 0:
                inds1, inds2 = zip(*edges_toadd)
                inds1 = np.array(inds1)
                inds2 = np.array(inds2)

                vs1 = g.vs[inds1]
                vs2 = g.vs[inds2]
                dists = haversine(
                    vs1["lon"],
                    vs1["lat"],
                    vs2["lon"],
                    vs2["lat"],
                )
                # Only keep distances of less than max_km
                mask_d = dists <= max_km
                inds1 = inds1[mask_d]
                inds2 = inds2[mask_d]
                dists = dists[mask_d]
                if len(dists) > 0:
                    # Determine the edges to add
                    edges = []
                    if single_connection:
                        # Only keep the closest connection between inds1 and inds2
                        v_i = dists.argmin()
                        source = inds1[v_i]
                        target = inds2[v_i]
                        edges += [(int(source), int(target))]
                    else:
                        # Keep only the closest found edge for each vertex from inds1
                        for source in np.unique(inds1):
                            v_i = np.where(inds1 == source)
                            target_i = dists[v_i].argmin()
                            target = inds2[v_i][target_i]
                            edges += [(int(source), int(target))]

                    # Add edges
                    g.add_edges(edges)


def connect_close_vertices(g, inds, max_km=5):
    # Connect vertices that are close together
    # Firt, try to connect the vertices of degree 1
    vs_all = g.vs.select(inds)
    vs_d1 = g.vs.select(inds, _degree=1)
    __connect_close_vertices(g, vs_d1.indices, vs_all.indices, max_km=max_km)
    # Then try to connect the remaining components together
    g.vs["id"] = g.vs.indices
    gs = g.induced_subgraph(inds)
    comps = gs.connected_components()
    for c in comps:
        vs_c_inds = gs.vs[c]["id"]
        vs_nc_inds = list(set(inds) - set(vs_c_inds))
        __connect_close_vertices(
            g, vs_c_inds, vs_nc_inds, max_km=max_km, single_connection=True
        )
    # Remove the "id" attribute
    del g.vs["id"]


def open_sea_graph():
    # Open the graph
    if not os.path.isfile("Shipping/sea_graph.pkl"):
        print("Create the shipping graph.")
        gdf = gp.read_file("Shipping/SeaGraph.geojson").explode()
        g = ig.Graph(directed=False)
        # 1. Create a graph with connect LineStrings
        # Create vertices
        coords = shapely.get_coordinates(gdf.geometry)
        g.add_vertices(n=len(coords))
        g.vs["lat"] = coords[:, 1].tolist()
        g.vs["lon"] = coords[:, 0].tolist()
        # Create edges
        # First, the ones in each LINESTRING from gdf.geometry
        edges = []
        next_vi = 0
        for geo in gdf.geometry:
            edges += [
                (vi, vi + 1) for vi in range(next_vi, next_vi + len(geo.coords) - 1)
            ]
            next_vi += len(geo.coords)
        g.add_edges(edges)
        # Merge vertices in same locations
        merge_vertices(g, g.vs.indices)
        # Connect close vertices
        connect_close_vertices(g, g.vs.indices, max_km=100)
        # Simplify the graph
        g.simplify()

        # Compute distances
        sources = ig.VertexSeq(g, [e.source for e in g.es])
        targets = ig.VertexSeq(g, [e.target for e in g.es])
        g.es["dist"] = haversine(
            sources["lon"], sources["lat"], targets["lon"], targets["lat"]
        ).tolist()
        # Add attributes
        g.vs["vtype"] = "sea"
        g.es["etype"] = "sea"
        g.write_pickle("Shipping/sea_graph.pkl")
    # Open the graph and return it
    return ig.read("Shipping/sea_graph.pkl", format="pickle")


def open_road_graph():
    # Create the graph if doesn't already exist
    if not os.path.isfile("Roads/road_graph.pkl"):
        print("Create Road Graph")
        # g = read_shapefile("Roads/ne_10m_roads.zip")
        # Load the shapefile
        gdf = gp.read_file("Roads/ne_10m_roads.zip").explode()
        g = ig.Graph(directed=False)
        # 1. Create a graph with connect LineStrings
        print("Create graph from raw data")
        # Create vertices
        coords = shapely.get_coordinates(gdf.geometry)
        g.add_vertices(n=len(coords))
        g.vs["lat"] = coords[:, 1].tolist()
        g.vs["lon"] = coords[:, 0].tolist()
        # Create edges
        edges = []
        next_vi = 0
        for geo in gdf.geometry:
            edges += [
                (vi, vi + 1) for vi in range(next_vi, next_vi + len(geo.coords) - 1)
            ]
            next_vi += len(geo.coords)
        g.add_edges(edges)

        # Get countries boundaries
        cdf = gp.read_file("Countries/countries_boundaries.zip")
        # Keep necessary info
        cdf = cdf[["iso3", "geometry"]]

        # 1. Merge vertices with identical location
        # Process by country to limit memory usage
        j = 1
        for i, c in cdf.iterrows():
            print(f"Merge vertices country: {j}/{len(cdf)} ({c.iso3})", end="\r")
            j += 1
            geoms = gp.points_from_xy(g.vs["lon"], g.vs["lat"])
            indices = np.array(g.vs.indices)
            geoms_c = c.geometry.buffer(1)
            inds = indices[shapely.contains(geoms_c, geoms)]
            merge_vertices(g, inds)

        # 2. Assign country to vertices
        # Note: vertices do not change anymore
        geoms = gp.points_from_xy(g.vs["lon"], g.vs["lat"])
        indices = np.array(g.vs.indices)
        j = 1
        for i, c in cdf.iterrows():
            print(f"Assign country to vertices: {j}/{len(cdf)} ({c.iso3})", end="\r")
            j += 1
            vs_in_c = indices[shapely.contains(c.geometry, geoms)]
            g.vs[vs_in_c]["country"] = c.iso3

        # Remove vertices without country
        g = g - g.vs.select(country=None)

        # 3. Connect close enough vertices
        # Process by country to limit memory usage
        geoms = gp.points_from_xy(g.vs["lon"], g.vs["lat"])
        indices = np.array(g.vs.indices)
        j = 1
        for i, c in cdf.iterrows():
            print(
                f"Connect close vertices country: {j}/{len(cdf)} ({c.iso3})", end="\r"
            )
            j += 1
            # Select vertices in an area a bit bigger than the country
            geoms_c = c.geometry.buffer(1)
            inds = indices[shapely.contains(geoms_c, geoms)]
            # Start with very close vertices
            connect_close_vertices(g, inds, max_km=20)
            # Check connected components
            # len(g.connected_components())
            # len(g.induced_subgraph(inds).connected_components())
            #
            # save components to shapefile
            # gs = g.induced_subgraph(inds)
            # g_comps = gs.connected_components()
            # g_comps = sorted(g_comps, key=len, reverse=True)
            #
            # for comp in range(0, len(g_comps)):
            # for comp in range(0, 4):
            #     gt = gs.induced_subgraph(g_comps[comp])
            #     write_shapefile(gt, f"{c.iso3}_comp_{comp}_lines.shp", geometry="lines")

        # Simplify the graph
        g.simplify()

        # 3. Assign country to edges
        j = 1
        for i, c in cdf.iterrows():
            print(f"Assign country to edges: {j}/{len(cdf)} ({c.iso3})", end="\r")
            j += 1
            # vs_in_c = indices[shapely.contains(c.geometry, geoms)]
            # es_in_c = g.es.select(_within=vs_in_c)
            es_in_c = g.es.select(_within=g.vs.select(country=c.iso3))
            es_in_c["country"] = c.iso3

        # # Check connected components
        # len(g.connected_components())
        # # Save components to shapefile
        # g_comps = g.connected_components()
        # g_comps = sorted(g_comps, key=len, reverse=True)
        #
        # for comp in [0, 1, 2, 3, 4]:
        #     gt = g.induced_subgraph(g_comps[comp])
        #     write_shapefile(gt, f"fg_comp_{comp}_lines.shp", geometry="lines")

        # Compute distances
        sources = ig.VertexSeq(g, [e.source for e in g.es])
        targets = ig.VertexSeq(g, [e.target for e in g.es])
        g.es["dist"] = haversine(
            sources["lon"], sources["lat"], targets["lon"], targets["lat"]
        ).tolist()

        # Add attributes
        g.vs["vtype"] = "road"
        g.es["etype"] = "road"
        # Save the graph
        g.write_pickle("Roads/road_graph.pkl")
    # Open the graph and return it
    return ig.read("Roads/road_graph.pkl", format="pickle")


def open_ports_graph():
    ports = pd.read_csv("Ports/WPS.csv", na_filter=False)
    g = ig.Graph(n=len(ports))
    for c in ports.columns:
        g.vs[c] = list(ports[c])
    g.vs["vtype"] = "port"
    return g


def open_cities_graph():
    # 1. World Cities
    cities = pd.read_csv("Cities/worldcities.csv")
    cities = cities[["city_ascii", "country", "iso3", "population", "lat", "lng"]]
    cities.rename(columns={"city_ascii": "city", "lng": "lon"}, inplace=True)
    # Correct country codes
    cities.loc[cities.iso3 == "XGZ", "iso3"] = "PSE"
    cities.loc[cities.iso3 == "XWB", "iso3"] = "PSE"
    cities.loc[cities.iso3 == "XKS", "iso3"] = "KSV"
    cities.loc[cities.iso3 == "XSV", "iso3"] = "SJM"
    cities.loc[37389, "iso3"] = "ALA"
    # Keep cities with more than 100 000 inhabitants
    cities = cities[cities.population > 100000]
    # Then for each country, keep the 10 more populated cities
    for iso3 in pd.unique(cities.iso3):
        cs = cities[cities.iso3 == iso3]
        if len(cs) > 10:
            minimum = np.sort(cs.population)[-10]
            to_drop = cs[cs.population < minimum]
            cities = cities.drop(to_drop.index)

    # 2. Main cities and capitals
    countries = pd.read_csv("Countries/countries_raw.csv")
    # Keep the list of landlocked countries
    ll_countries = countries[["iso3", "landlocked"]].drop_duplicates()
    countries = countries[["city", "country", "iso3", "cap", "maincity", "lat", "lon"]]

    # 3. Merge info
    cities_all = cities.merge(countries, how="outer", on=["city", "iso3"])
    cities_all["lat"] = cities_all.lat_y.combine_first(cities_all.lat_x)
    cities_all["lon"] = cities_all.lon_y.combine_first(cities_all.lon_x)
    cities_all = cities_all[["city", "iso3", "maincity", "cap", "lat", "lon"]]
    cities_all.loc[cities_all.maincity.isna(), "maincity"] = 0
    cities_all.loc[cities_all.cap.isna(), "cap"] = 0
    cities_all = cities_all.merge(ll_countries, how="left", on="iso3")
    cities_all.rename(
        columns={"city": "name", "cap": "capital", "iso3": "country"}, inplace=True
    )

    # 4. Create the graph
    g = ig.Graph(n=len(cities_all))
    for c in cities_all.columns:
        g.vs[c] = list(cities_all[c])
    g.vs["vtype"] = "city"
    return g


def connect_ports_to_sea(g):
    ps = g.vs.select(vtype="port")
    vs_sea = g.vs.select(vtype="sea")
    max_km = 50
    while len(ps) > 0:
        # print(f"{max_km}: Before {len(ps)}")
        __connect_close_vertices(g, ps.indices, vs_sea.indices, max_km=max_km)
        ps = g.vs.select(vtype="port", _degree=0)
        # print(f"{max_km}: After {len(ps)}")
        max_km *= 10
    # Compute distances
    ps = g.vs.select(vtype="port")
    es = g.es.select(_between=(ps.indices, vs_sea.indices))
    sources = ig.VertexSeq(g, [e.source for e in es])
    targets = ig.VertexSeq(g, [e.target for e in es])
    es["dist"] = haversine(
        sources["lon"], sources["lat"], targets["lon"], targets["lat"]
    ).tolist()
    es["etype"] = "sea"


def connect_ports_to_sea_old(g):
    ps = g.vs.select(vtype="port")
    # Points of all sea vertices
    vs_sea = g.vs.select(vtype="sea")
    vs_sea_indices = np.array(vs_sea.indices)
    geoms = np.array([Point(v["lon"], v["lat"]) for v in vs_sea])
    for p in ps:
        # Find closest sea vertex
        radius = 5
        found = False
        while not found:
            buff = Point(p["lon"], p["lat"]).buffer(radius, resolution=8)
            # Get all sea vertices in the buffer
            vs_sea_in = g.vs[vs_sea_indices[shapely.contains(buff, geoms)]]
            if len(vs_sea_in) > 0:
                found = True
            else:
                radius += 5
        dist = 1e10
        index = -1
        for v in vs_sea_in:
            dist_v = great_circle((p["lat"], p["lon"]), (v["lat"], v["lon"])).km
            if dist_v < dist:
                dist = dist_v
                index = v.index
        g.add_edge(p.index, index, etype="sea", dist=dist)


def connect_ports_to_road(g):
    ps = g.vs.select(vtype="port")
    # Points of all road and cities vertices
    # Note: Ports can be connected directly to cities when
    # no road is available in a country (e.g. small island)
    vs_road = g.vs.select(vtype_in=["road", "city"])
    __connect_close_vertices(g, ps.indices, vs_road.indices, max_km=500)
    # Here, 26 ports not connected (some remote islands have ports but no cities nor roads)

    # Compute distances
    ps = g.vs.select(vtype="port")
    es = g.es.select(_between=(ps.indices, vs_road.indices))
    sources = ig.VertexSeq(g, [e.source for e in es])
    targets = ig.VertexSeq(g, [e.target for e in es])
    es["dist"] = haversine(
        sources["lon"], sources["lat"], targets["lon"], targets["lat"]
    ).tolist()
    es["etype"] = "road"


def connect_ports_to_road_old(g):
    ps = g.vs.select(vtype="port")
    # Points of all road and cities vertices
    # Note: Ports can be connected directly to cities when
    # no road is available in a country (e.g. small island)
    vs_road = g.vs.select(vtype_in=["road", "city"])
    vs_road_indices = np.array(vs_road.indices)
    geoms = np.array([Point(v["lon"], v["lat"]) for v in vs_road])
    noconn = []
    for p in ps:
        # Find closest road vertex in a given radius
        radius = 10
        buff = Point(p["lon"], p["lat"]).buffer(radius, resolution=8)
        # Get all sea vertices in the buffer
        vs_road_in = g.vs[vs_road_indices[shapely.contains(buff, geoms)]]
        if len(vs_road_in) > 0:
            dist = 1e10
            index = -1
            for v in vs_road_in:
                dist_v = great_circle((p["lat"], p["lon"]), (v["lat"], v["lon"])).km
                if dist_v < dist:
                    dist = dist_v
                    index = v.index
            g.add_edge(p.index, index, etype="road", dist=dist)
        else:
            # No close road vertex found
            noconn += [{"name": p["name"], "country": p["country"], "index": p.index}]

    nc = g.vs.select([nc["index"] for nc in noconn])
    nc["connected"] = False


def connect_cities(g):
    # Checks:
    # Every city should be connected to either:
    # - A road from its country
    # - A port from its country
    # - Or directly to the sea.

    countries = np.unique(g.vs.select(vtype="city")["country"])

    vs_sea = g.vs.select(vtype="sea")
    for c in countries:
        print(f"{c}", end="\r")
        # Connect cities to closest road or port
        cities = g.vs.select(vtype="city", country=c)
        vs_road = g.vs.select(vtype_in=["road", "port"], country=c)
        __connect_close_vertices(g, cities.indices, vs_road.indices, max_km=50)
        # Some cities are a bit further
        cities = g.vs.select(vtype="city", _degree=0, country=c)
        __connect_close_vertices(g, cities.indices, vs_road.indices, max_km=500)
        # If no road and no port, connect to sea directly
        cities = g.vs.select(vtype="city", _degree=0, country=c)
        __connect_close_vertices(g, cities.indices, vs_sea.indices, max_km=500)

    # Note: We might be missing cities that may be connected to nearby neighbors roads.
    cities = g.vs.select(vtype="city")
    vs_road = g.vs.select(vtype_in=["road", "port"])
    __connect_close_vertices(g, cities.indices, vs_road.indices, max_km=20)

    # Compute distances
    es = g.es.select(_between=(cities.indices, vs_road.indices))
    sources = ig.VertexSeq(g, [e.source for e in es])
    targets = ig.VertexSeq(g, [e.target for e in es])
    es["dist"] = haversine(
        sources["lon"], sources["lat"], targets["lon"], targets["lat"]
    ).tolist()
    es["etype"] = "road"

    cities = g.vs.select(vtype="city")
    es = g.es.select(_between=(cities.indices, vs_sea.indices))
    sources = ig.VertexSeq(g, [e.source for e in es])
    targets = ig.VertexSeq(g, [e.target for e in es])
    es["dist"] = haversine(
        sources["lon"], sources["lat"], targets["lon"], targets["lat"]
    ).tolist()
    es["etype"] = "sea"


def connect_cities_to_road_old(g):
    # cs = g.vs.select(vtype="city")
    # # 1 Connect cities to roads
    # # Points of all road vertices
    # vs_road = g.vs.select(vtype="road")
    # vs_port = g.vs.select(vtype="port")
    # vs_road_indices = np.array(vs_road.indices)
    # geoms = np.array([Point(v["lon"], v["lat"]) for v in vs_road])

    # Connect cities to closest road. If no road in country, connect to closest port
    # Loop over countries to not recompute geoms
    noconn = []
    countries = np.unique(g.vs.select(vtype="city")["country"])
    # # Get all the roads for when same-country roads are too far
    vs_road_all = g.vs.select(vtype="road")
    vs_road_all_indices = np.array(vs_road_all.indices)
    geoms_road = np.array([Point(v["lon"], v["lat"]) for v in vs_road_all])
    # Get the sea routes for when ports are too far
    vs_sea = g.vs.select(vtype="sea")
    vs_sea_indices = np.array(vs_sea.indices)
    geoms_sea = np.array([Point(v["lon"], v["lat"]) for v in vs_sea])

    def connect_to_sea(c, noconn):
        # Try to connect to closest sea vertex
        radius = 50
        buff = Point(c["lon"], c["lat"]).buffer(radius, resolution=8)
        vs_sea_in = g.vs[vs_sea_indices[shapely.contains(buff, geoms_sea)]]
        if len(vs_sea_in) > 0:
            # Find the closest sea (not too many ports)
            dist = 1e10
            index = -1
            for v in vs_sea_in:
                dist_v = great_circle((c["lat"], c["lon"]), (v["lat"], v["lon"])).km
                if dist_v < dist:
                    dist = dist_v
                    index = v.index
            # Add the edge to the graph
            g.add_edge(c.index, index, etype="road", dist=dist)
        else:
            noconn += [{"name": c["name"], "country": c["country"], "index": c.index}]
            print(f"Couldn't connect to sea vertex.")

    def connect_to_any_road(c, noconn):
        # Try to connect to closest road
        radius = 50
        buff = Point(c["lon"], c["lat"]).buffer(radius, resolution=8)
        vs_road_in = g.vs[vs_road_all_indices[shapely.contains(buff, geoms_road)]]
        if len(vs_road_in) > 0:
            # Find the closest sea (not too many ports)
            dist = 1e10
            index = -1
            for v in vs_road_in:
                dist_v = great_circle((c["lat"], c["lon"]), (v["lat"], v["lon"])).km
                if dist_v < dist:
                    dist = dist_v
                    index = v.index
            # Add the edge to the graph
            g.add_edge(c.index, index, etype="road", dist=dist)
        else:
            noconn += [{"name": c["name"], "country": c["country"], "index": c.index}]
            print(f"Couldn't connect to any other road.")

    for country in countries:
        print(f"{country}", end="\r")
        # Get the roads
        # Note: Cities can be connected directly to ports when
        # no road is available in a country (e.g. small island)
        vs_road = g.vs.select(vtype_in=["road", "port"], country=country)
        vs_road_indices = np.array(vs_road.indices)
        geoms = np.array([Point(v["lon"], v["lat"]) for v in vs_road])
        # Get the ports
        # vs_port = g.vs.select(vtype="port", country=country)
        # vs_port_indices = np.array(vs_port.indices)
        # Loop over the cities in the countries
        csc = g.vs.select(vtype="city", country=country)
        for c in csc:
            found_close_road = False
            # Get the roads in the country
            # vs_road_country = vs_road.select(country=c["country"])
            # vs_road_country_indices = np.array(vs_road_country.indices)
            # geoms = np.array([Point(v["lon"], v["lat"]) for v in vs_road_country])
            if len(vs_road) > 0:
                # Get the closest roads
                vs_road_in = []
                found = False
                radius = 0.1
                while len(vs_road_in) == 0:
                    radius *= 2
                    buff = Point(c["lon"], c["lat"]).buffer(radius, resolution=8)
                    vs_road_in = g.vs[vs_road_indices[shapely.contains(buff, geoms)]]
                # Find the closest road vertex in the country
                dist = 1e10
                index = -1
                for v in vs_road_in:
                    dist_v = great_circle((c["lat"], c["lon"]), (v["lat"], v["lon"])).km
                    if dist_v < dist:
                        dist = dist_v
                        index = v.index

                if dist < 100:
                    found_close_road = True
                    # Add the edge to the graph
                    g.add_edge(c.index, index, etype="road", dist=dist)

            if not found_close_road:
                if c["landlocked"] == 0:
                    # Try to connect to closest sea vertex if not landlocked country
                    print(
                        f"Could not find close road for {c['name']} in {c['country']}. Trying to connect to sea vertex..."
                    )
                    connect_to_sea(c, noconn)
                else:
                    print(
                        f"Could not find close road for {c['name']} in {c['country']}. Trying to connect to any other road..."
                    )
                    connect_to_any_road(c, noconn)


def _has_country(country):
    return (
        country is not None
        and country != ""
        and country != "None"
        and not pd.isna(country)
    )


def correct_vertices_types(g):
    # Assign country labels to sea vertices that are strictly inside country polygons.
    if "country" not in g.vs.attributes():
        g.vs["country"] = None

    cdf = gp.read_file("Countries/countries_boundaries.zip")
    cdf = cdf[["iso3", "geometry"]]

    vs_sea = g.vs.select(vtype="sea")
    if len(vs_sea) == 0:
        return

    geoms = gp.points_from_xy(vs_sea["lon"], vs_sea["lat"])
    indices = np.array(vs_sea.indices)
    j = 1
    for i, c in cdf.iterrows():
        print(
            f"Assign country to sea vertices: {j}/{len(cdf)} ({c.iso3})",
            end="\r",
        )
        j += 1
        vs_in_c = indices[shapely.contains(c.geometry, geoms)]
        g.vs[vs_in_c]["country"] = c.iso3


def remove_invalid_landlocked_city_sea_edges(g):
    bad_edges = []
    for e in g.es.select(etype="sea"):
        endpoints = [g.vs[e.source], g.vs[e.target]]
        has_landlocked_city = any(
            v["vtype"] == "city" and bool(v["landlocked"]) for v in endpoints
        )
        has_sea_vertex = any(v["vtype"] == "sea" for v in endpoints)
        if has_landlocked_city and has_sea_vertex:
            bad_edges.append(e.index)

    if len(bad_edges) > 0:
        g.delete_edges(bad_edges)


def correct_edges_types(g):
    # Label connections to ports and differently
    # For use in shortest-path later
    seas = g.es.select(etype="sea")
    for s in seas:
        source = s.source
        target = s.target
        connected = set(g.incident(source)) | set(g.incident(target))
        roads = g.es.select(connected).select(etype="road")
        # Assign the type "road_sea"
        if len(roads) > 0:
            roads["etype"] = "road_sea"
            # Make sure a country is assigned to the edges
            for r in roads:
                if r["country"] is None:
                    # Find closest vertice with an assigned country
                    if g.vs(r.source)[0]["country"] is not None:
                        r["country"] = g.vs(r.source)[0]["country"]
                    elif g.vs(r.target)[0]["country"] is not None:
                        r["country"] = g.vs(r.target)[0]["country"]
                    else:
                        print(r)
                        raise Error(f"Cannot determine country for road_sea index {r}")

    # Label the roads that cross countries (and missing country labels)
    roads_no_country = g.es.select(etype="road", country=None)
    for r in roads_no_country:
        c_target = g.vs[r.target]["country"]
        c_source = g.vs[r.source]["country"]
        if g.vs[r.target]["country"] != g.vs[r.source]["country"]:
            r["etype"] = "road_border"
            r["country1"] = c_source
            r["country2"] = c_target
        else:
            r["country"] = g.vs[r.target]["country"]

    # Label sea edges that cross between country-labeled water vertices.
    sea_edges = g.es.select(etype="sea")
    for s in sea_edges:
        c_source = g.vs[s.source]["country"]
        c_target = g.vs[s.target]["country"]
        if _has_country(c_source) and _has_country(c_target):
            if c_source != c_target:
                s["etype"] = "sea_border"
                s["country1"] = c_source
                s["country2"] = c_target
            else:
                s["country"] = c_source


def check_connected_components(g, name):
    len(g.connected_components())
    # Save components to shapefile
    g_comps = g.connected_components()
    g_comps = sorted(g_comps, key=len, reverse=True)

    for comp in range(0, min(4, len(g_comps))):
        gt = g.induced_subgraph(g_comps[comp])
        write_shapefile(gt, f"{name}_comp_{comp}_lines.shp", geometry="lines")


# Open and combine all graphs
print("Open the separate graphs (road, sea, ports, cities).")
g = open_road_graph() + open_sea_graph() + open_ports_graph() + open_cities_graph()

# Connect ports to sea graph
print("Connect ports to sea.")
connect_ports_to_sea(g)
g.write_pickle("FullGraph/graph1.pkl")
# g = ig.read("FullGraph/graph1.pkl", format="pickle")

print("Connect ports to road/cities.")
connect_ports_to_road(g)
g.write_pickle("FullGraph/graph2.pkl")
# g = ig.read("FullGraph/graph2.pkl", format="pickle")

# Connect cities to road graph
print("Connect cities to roads/ports.")
connect_cities(g)
g.write_pickle("FullGraph/graph3.pkl")
# g = ig.read("FullGraph/graph3.pkl", format="pickle")

# Correct some edges types
print("Correct some vertices types.")
correct_vertices_types(g)

print("Remove invalid landlocked city-sea edges.")
remove_invalid_landlocked_city_sea_edges(g)

print("Correct some edges types.")
correct_edges_types(g)

# Save the final graph
print("Save Full Graph")
g.simplify(combine_edges="first")
g = g.as_undirected()
g.write_pickle("FullGraph/fullgraph.pkl")
g.write_graphml("FullGraph/fullgraph.graphml")
# g = ig.read("FullGraph/fullgraph.pkl", format="pickle")
write_shapefile(g, "FullGraph/fullgraph_points.shp", geometry="points")
write_shapefile(g, "FullGraph/fullgraph_lines.shp", geometry="lines")


###################
# Neighbors Graph #
###################

print("Create Borders Graph.")

# Open the borders file
borders = pd.read_csv("Countries/neighbourCountries.csv")

# Create the graph
g = ig.Graph()

# For each border
is_empty = True
for i in range(0, len(borders["iso1"].tolist())):
    # If the first or second country does not exist in the vertices set, create
    # them.
    if is_empty or borders.iloc[i]["iso1"] not in g.vs["name"]:
        g.add_vertex(borders.iloc[i]["iso1"])
    if is_empty or borders.iloc[i]["iso2"] not in g.vs["name"]:
        g.add_vertex(borders.iloc[i]["iso2"])
    is_empty = False
    # Add the edge between the 2 countries
    c1 = g.vs.find(borders.iloc[i]["iso1"])
    c2 = g.vs.find(borders.iloc[i]["iso2"])
    g.add_edge(c1, c2, length=borders.iloc[i]["border_length"])

# Write the graph to file
g = g.as_undirected()
print("Save Borders Graph.")
g.write_pickle("FullGraph/bordersgraph.pkl")
g.write_graphml("FullGraph/bordersgraph.graphml")
