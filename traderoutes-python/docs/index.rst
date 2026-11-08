Traderoutes
===========

**traderoutes** is a Python package for querying border relationships between
countries and computing shortest-path trade routes on a worldwide transportation
network that combines roads, shipping lanes, and port connections.

Installation
------------

.. code-block:: bash

   pip install -e /path/to/traderoutes

Quick start
-----------

**Border queries**

.. code-block:: python

   import traderoutes as tr

   tr.are_neighbors("FRA", "ITA")          # True
   tr.get_neighbors("FRA")                 # ['AND', 'BEL', ...]
   tr.get_common_neighbors("FRA", "ITA")   # ['CHE']

**Route computation**

.. code-block:: python

   import traderoutes as tr

   fra = tr.get_main_city("FRA")
   nld = tr.get_main_city("NLD")

   # Road cost 7× sea cost; high port cost to discourage sea routes
   path = tr.get_path(fra, nld, road_cost=7, port_cost=1e4)
   print(tr.get_pattern(path))          # e.g. 'crc'
   print(tr.road_distance(path))        # km of roads
   print(tr.sea_distance(path))         # km of sea and sea-border edges
   print(tr.transits_i(path))           # e.g. ['BEL']

   # Export to KML for Google Earth
   tr.to_kml(path, "fra_nld.kml")

API reference
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api/borders
   api/routes
