# traderoutes for R

`traderoutes` provides country-border queries and weighted shortest-path trade
routes on a worldwide road, port, and shipping network.

The R package bundles the precomputed GraphML assets required at runtime under
`inst/extdata/`. Users do not need the graph-generation code or a Docker
container to install and use the package.

## Installation

Install the local source package with:

```r
install.packages("/path/to/traderoutes-r", repos = NULL, type = "source")
```

The package requires R 4.1 or newer and imports `igraph`.

## Quick start

```r
library(traderoutes)

are_neighbors("FRA", "ITA")
get_neighbors("FRA")
get_common_neighbors("FRA", "ITA")

origin <- get_main_city("FRA")
destination <- get_main_city("NLD")
path <- get_path(origin, destination, road_cost = 7, port_cost = 1e4)

get_pattern(path)
road_distance(path)
sea_distance(path)
transits_i(path)
transits_j(path)
```

## Package data

The package expects these files under `inst/extdata/`:

```text
inst/extdata/bordersgraph.graphml
inst/extdata/fullgraph.graphml
```

They are already present in this repository and are generated from the
canonical graph outputs. The files are large and may be stored through Git
LFS, so retrieve the actual objects before building:

```bash
git lfs pull
```

## Docker targets

The [`Dockerfile`](Dockerfile) provides reproducible development, testing, and
build environments. Build from this directory:

```bash
docker build --target dev -t traderoutes-r-dev .
docker build --target build-env -t traderoutes-r-build-env .
docker build --target test -t traderoutes-r-test .
docker build --target build -t traderoutes-r-build .
```

The stages have different purposes:

- `dev` provides an interactive R environment with the source tree at
  `/workspace`.
- `build-env` provides only the R build/check toolchain. Mount the source and
  output directories to write artifacts directly to the host.
- `test` installs the package, verifies the bundled GraphML files, loads the
  package, and runs the `testthat` suite.
- `build` creates the R source package and runs `R CMD check` on it.

The `test` stage runs its tests during `docker build`, so a failing test causes
the image build to fail. It also has the test command as its default container
command, so a successful image can be tested again:

```bash
docker run --rm traderoutes-r-test
```

The build stage does not publish the package and does not require repository
credentials. For local development, build and check directly into a host
directory with Podman:

```bash
mkdir -p dist
podman run --rm \
  -v "$PWD:/workspace:Z" \
  -v "$PWD/dist:/out:Z" \
  traderoutes-r-build-env \
  sh -c 'cd /out && R CMD build --no-manual --no-build-vignettes /workspace && R CMD check --no-manual --no-vignettes --no-build-vignettes traderoutes_*.tar.gz'
```

## Local tests

With R, `igraph`, and `testthat` installed:

```bash
Rscript --vanilla -e 'testthat::test_local(".")'
```

The package checks can also be run with:

```bash
R CMD build .
R CMD check traderoutes_*.tar.gz
```

## Main API

| Function | Description |
|---|---|
| `are_neighbors(c1, c2)` | Whether two countries share a land border |
| `get_neighbors(c)` | Neighboring ISO3 country codes |
| `get_second_neighbors(c)` | Countries two border hops away |
| `get_common_neighbors(c1, c2)` | Countries neighboring both inputs |
| `countries()` | Countries represented in the transportation graph |
| `get_main_city(c)` | Main city vertex for a country |
| `get_great_circle(c1, c2)` | Great-circle distance in km |
| `get_path(v1, v2, ...)` | Weighted shortest path |
| `get_pattern(path)` | Compact path vertex-type pattern |
| `get_countries(path, ...)` | Country segments and distances |
| `road_distance(path)` | Road distance in km |
| `sea_distance(path)` | Sea distance in km |
| `transits_i(path, ...)` | Origin-side transit countries |
| `transits_j(path, ...)` | Destination-side transit countries |

## License

MIT; see [`LICENSE`](LICENSE).
