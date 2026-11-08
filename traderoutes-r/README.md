# traderoutes

An R package for querying country border relationships and computing weighted
shortest-path international trade routes on a combined road/sea transportation
network.

## Prerequisites

The package expects these two GraphML files to be bundled in the source tree.
They are produced by the graph creation pipeline and should be copied into
`inst/extdata/` before installing or testing the package:

- `Data/Routes_Packages/R/traderoutes/inst/extdata/bordersgraph.graphml`
- `Data/Routes_Packages/R/traderoutes/inst/extdata/fullgraph.graphml`

Once those files are present under `inst/extdata/`, they are installed with the
package automatically.

If you already have the GraphML exports, copy them into place before installing
or testing the package:

```bash
cp /path/to/bordersgraph.graphml \
  Data/Routes_Packages/R/traderoutes/inst/extdata/bordersgraph.graphml
cp /path/to/fullgraph.graphml \
  Data/Routes_Packages/R/traderoutes/inst/extdata/fullgraph.graphml
```

## Installation

```r
# Install from local source
install.packages("/path/to/Routes_Packages/R/traderoutes",
                 repos = NULL, type = "source")
```

## Docker

From `Data/Routes_Packages/R/traderoutes/`:

```bash
docker build -t holdup_route_r .
docker create -it --name holdup_route_r holdup_route_r
docker start -ai holdup_route_r
```

The image build now copies the package source into `/traderoutes`, checks that
`inst/extdata/bordersgraph.graphml` and `inst/extdata/fullgraph.graphml` are
present, and installs the package during the image build. Once the container
starts, it is ready to use immediately.

Inside the container:

```bash
Rscript --vanilla -e 'library(traderoutes)'
Rscript --vanilla -e 'testthat::test_local("/traderoutes")'
```

## Quick start

```r
library(traderoutes)

# --- Border queries ---
are_neighbors("FRA", "ITA")           # TRUE
are_neighbors("FRA", "USA")           # FALSE
get_neighbors("FRA")
get_common_neighbors("FRA", "ITA")    # "CHE"

# --- Route computation ---
v_fra <- get_main_city("FRA")
v_nld <- get_main_city("NLD")

# Road cost 7x sea cost; high port cost discourages sea
path <- get_path(v_fra, v_nld, road_cost = 7, port_cost = 1e4)
get_pattern(path)        # e.g. "crc"
road_distance(path)      # km of road
sea_distance(path)       # km of sea and sea-border edges
transits_i(path)         # transit countries from origin

# Great-circle distance
get_great_circle("FRA", "ITA")   # ~1109.56 km
```

## API

| Function | Description |
|---|---|
| `are_neighbors(c1, c2)` | `TRUE` if countries share a land border |
| `get_neighbors(c)` | Neighboring country codes |
| `get_second_neighbors(c)` | Countries 2 hops away |
| `get_common_neighbors(c1, c2)` | Countries neighboring both |
| `countries()` | All countries in the network |
| `get_main_city(c)` | Vertex index of main city |
| `get_great_circle(c1, c2)` | Great-circle distance (km) |
| `get_path(v1, v2, ...)` | Weighted shortest path |
| `get_pattern(path)` | Vertex-type pattern string |
| `get_countries(path, ...)` | Country segments with distances |
| `road_distance(path)` | Total road distance (km) |
| `sea_distance(path)` | Total sea and sea-border distance (km) |
| `transits_i(path, ...)` | Origin-side transit countries |
| `transits_j(path, ...)` | Destination-side transit countries |

## Tests

```r
devtools::test()
```

## License

MIT
