# traderoutes

A Python package for querying country border relationships and computing
shortest-path international trade routes on a combined road/sea transportation
network.

## Installation

```bash
pip install traderoutes
```

For development from this repository:

```bash
python -m pip install -e .
```

## Requirements

- Python ≥ 3.10
- numpy, igraph, geopy, simplekml

## Quick start

### Border queries

```python
import traderoutes as tr

# Check whether two countries share a land border
tr.are_neighbors("FRA", "ITA")          # True
tr.are_neighbors("FRA", "USA")          # False

# List all neighbors
tr.get_neighbors("FRA")                 # ['AND', 'BEL', 'DEU', ...]

# Countries two hops away (excluding direct neighbors)
tr.get_second_neighbors("FRA")          # ['MAR', 'PRT', 'AUT', ...]

# Countries bordering both inputs
tr.get_common_neighbors("FRA", "ITA")   # ['CHE']
```

### Route computation

```python
import traderoutes as tr

fra = tr.get_main_city("FRA")
nld = tr.get_main_city("NLD")

# Shortest path with road cost 7x sea cost
path = tr.get_path(fra, nld, road_cost=7, port_cost=1e4)

tr.get_pattern(path)      # 'crc'  (city-road-city, land only)
tr.road_distance(path)    # km of road segments
tr.sea_distance(path)     # km of sea and sea-border segments
tr.transits_i(path)       # transit countries from origin side
tr.transits_j(path)       # transit countries from destination side

# Great-circle distance between capitals
tr.get_great_circle("FRA", "ITA")   # ~1109.56 km

# Export to KML for Google Earth
tr.to_kml(path, "fra_nld.kml")
```

## API overview

| Function | Description |
|---|---|
| `are_neighbors(c1, c2)` | `True` if countries share a land border |
| `get_neighbors(c)` | List of neighboring countries |
| `get_second_neighbors(c)` | Countries 2 hops away |
| `get_common_neighbors(c1, c2)` | Countries neighboring both |
| `countries()` | All countries with a main city in the graph |
| `get_main_city(c)` | Main city vertex for a country |
| `get_great_circle(c1, c2)` | Great-circle distance in km |
| `get_path(v1, v2, ...)` | Weighted shortest path between vertices |
| `get_pattern(path)` | String encoding of path vertex types |
| `get_countries(path, ...)` | Country segments with distances |
| `road_distance(path)` | Total road distance in km |
| `sea_distance(path)` | Total sea and sea-border distance in km |
| `transits_i(path, ...)` | Transit countries from origin side |
| `transits_j(path, ...)` | Transit countries from destination side |
| `to_kml(path, file)` | Export path to KML |

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT
