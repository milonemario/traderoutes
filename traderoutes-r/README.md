# traderoutes for R

`traderoutes` provides country-border queries and weighted shortest-path trade
routes on a worldwide road, port, and shipping network.

The R package bundles the precomputed GraphML assets required at runtime under
`inst/extdata/`. Users do not need the graph-generation code or a container
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

## Podman targets

The [`Dockerfile`](Dockerfile) provides reproducible development, testing, and
build environments. Build from this directory:

```bash
podman build --target build-env -t traderoutes-r-build-env .
podman build --target test -t traderoutes-r-test .
podman build --target build -t traderoutes-r-build .
```

The stages have different purposes:

- `build-env` provides only the R build/check toolchain. Mount the source and
  output directories to write artifacts directly to the host.
- `test` installs the package, verifies the bundled GraphML files, loads the
  package, and runs the `testthat` suite.
- `build` creates the R source package and runs `R CMD check` on it.

The `test` stage runs its tests during `podman build`, so a failing test causes
the image build to fail. It also has the test command as its default container
command, so a successful image can be tested again:

```bash
podman run --rm traderoutes-r-test
```

## Local tests

With R, `igraph`, and `testthat` installed, run the source-tree tests with:

```bash
Rscript --vanilla -e 'testthat::test_local(".")'
```

To build and check the release tarball in the Podman build environment while
writing the artifact directly to the host:

```bash
mkdir -p dist

podman run --rm \
  -v "$PWD:/workspace:Z" \
  -v "$PWD/dist:/out:Z" \
  traderoutes-r-build-env \
  sh -c 'cd /out && \
    Rscript --vanilla -e "roxygen2::roxygenise(\"/workspace\")" && \
    R CMD build --no-manual --no-build-vignettes /workspace && \
    R CMD check --no-manual --no-vignettes \
      --no-build-vignettes traderoutes_*.tar.gz'
```

Install and smoke-test the exact checked tarball:

```bash
podman run --rm \
  -v "$PWD/dist:/dist:Z" \
  traderoutes-r-build-env \
  sh -c 'R CMD INSTALL /dist/traderoutes_0.0.1.tar.gz && \
    Rscript --vanilla -e "library(traderoutes); print(head(countries()))"'
```

For a stricter CRAN-style check, run:

```bash
mkdir -p cran-check

podman run --rm \
  -v "$PWD:/workspace:Z" \
  -v "$PWD/cran-check:/out:Z" \
  traderoutes-r-build-env \
  sh -c 'cd /out && R CMD check --as-cran /workspace/dist/traderoutes_0.0.1.tar.gz'
```

Use a fresh `cran-check` directory for each run. This prevents an old
`.Rcheck` directory from being reused and confusing the result.

Replace `0.0.1` in these commands if the package version changes. The
`--as-cran` check should pass without errors or warnings before a CRAN
submission is considered.

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
