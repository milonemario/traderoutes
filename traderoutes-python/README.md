# traderoutes for Python

`traderoutes` provides country-border queries and weighted shortest-path trade
routes on a worldwide road, port, and shipping network.

The package bundles the precomputed graph assets required at runtime. Users do
not need the graph-generation code or a Docker container to install and use
the published package.

## Installation

```bash
python -m pip install traderoutes
```

For development from this repository:

```bash
python -m pip install -e .
```

The package requires Python 3.10 or newer. Runtime dependencies are declared
in [`pyproject.toml`](pyproject.toml).

## Quick start

```python
import traderoutes as tr

tr.are_neighbors("FRA", "ITA")       # True
tr.get_neighbors("FRA")              # neighboring ISO3 codes

origin = tr.get_main_city("FRA")
destination = tr.get_main_city("NLD")
path = tr.get_path(origin, destination, road_cost=7, port_cost=1e4)

tr.get_pattern(path)                  # e.g. "crc"
tr.road_distance(path)                # road distance in km
tr.sea_distance(path)                 # sea distance in km
tr.transits_i(path)
tr.transits_j(path)
tr.to_kml(path, "fra_nld.kml")
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
| `to_kml(path, file)` | Export a path to KML |

## Docker targets

The [`Dockerfile`](Dockerfile) provides reproducible development, testing, and
build environments. Build from this directory after retrieving Git LFS files:

```bash
git lfs pull
docker build --target build-env -t traderoutes-python-build-env .
docker build --target test -t traderoutes-python-test .
docker build --target build -t traderoutes-python-build .
docker build --target wheel-test -t traderoutes-python-wheel-test .
```

The stages have different purposes:

- `build-env` provides only the build toolchain. Mount the source and output
  directories to write artifacts directly to the host. It can also be used as
  an interactive development environment by mounting the source tree.
- `test` installs the package from the source tree and runs the unit tests.
- `build` creates the wheel and source distribution under `/dist`.
- `wheel-test` installs the built wheel and runs the tests against that exact
  wheel, which is the release artifact to be uploaded to PyPI.

The `test` and `wheel-test` stages run their tests during `docker build`, so a
failing test causes the image build to fail. They also have test commands as
their default container commands, so a successful image can be tested again:

```bash
docker run --rm traderoutes-python-test
docker run --rm traderoutes-python-wheel-test
```

The build stages do not publish anything and do not require PyPI credentials.
For local development, build directly into a host directory with Podman:

```bash
mkdir -p dist/python
podman run --rm \
  -v "$PWD:/workspace:Z" \
  -v "$PWD/dist/python:/out:Z" \
  traderoutes-python-build-env \
  python -m build --outdir /out
```

To test the exported wheel in the same clean toolchain:

```bash
podman run --rm \
  -v "$PWD:/workspace:Z" \
  -v "$PWD/dist/python:/dist:Z" \
  traderoutes-python-build-env \
  sh -c 'python -m pip install --no-cache-dir --no-deps /dist/*.whl && python -m unittest discover -s /workspace/tests -v'
```

## Local tests

With the runtime dependencies installed:

```bash
python -m unittest discover -s tests -v
```

## License

MIT; see [`LICENSE`](LICENSE).
