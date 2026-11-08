# traderoutes

This repository contains the graph-generation pipeline and the Python and R
packages used to query country borders and compute weighted international trade
routes.

## Repository layout

- `graph/` contains the graph-building code, source data, and generated graph
  artifacts.
- `traderoutes-python/` contains the Python package, published to PyPI.
- `traderoutes-r/` contains the R package, published independently.

The graph assets used by the packages are committed with Git LFS. The ZIP
archives are the canonical Natural Earth source inputs; extracted copies are
local build inputs and are ignored by Git.

## Packages

### Python

See [`traderoutes-python/README.md`](traderoutes-python/README.md).

Install the local package in editable mode with:

```bash
python -m pip install -e ./traderoutes-python
```

### R

See [`traderoutes-r/README.md`](traderoutes-r/README.md).

Install the local package with:

```r
install.packages("traderoutes-r", repos = NULL, type = "source")
```

## Rebuilding the graph

The graph pipeline is maintained under `graph/`. Its dependencies are listed
in [`graph/requirements.txt`](graph/requirements.txt). The generated package
assets should be updated together when the graph changes:

- Python: `FullGraph/*.pkl`
- R: `FullGraph/*.graphml`

Graph source provenance and download links are documented in
[`graph/README.md`](graph/README.md).

## Container workflows

The container files provide reproducible development, test, and build targets
using Podman.
Build them from the corresponding directories after checking out the Git LFS
assets:

```bash
git lfs pull

podman build --target build-env -t traderoutes-python-build-env ./traderoutes-python
podman build --target test  -t traderoutes-python-test ./traderoutes-python
podman build --target build -t traderoutes-python-build ./traderoutes-python
podman build --target wheel-test -t traderoutes-python-wheel-test ./traderoutes-python

podman build --target build-env -t traderoutes-r-build-env ./traderoutes-r
podman build --target test  -t traderoutes-r-test ./traderoutes-r
podman build --target build -t traderoutes-r-build ./traderoutes-r
```

The graph-generation container is separate because it has a different
geospatial toolchain:

```bash
podman build -t traderoutes-graph ./graph
```

Package build targets create artifacts but do not upload them. Publishing is a
separate release step performed after the artifacts have been tested.

## License

The repository code is released under the MIT License. Individual source data
sets may have additional attribution or licensing requirements; see the source
documentation in `graph/` before redistribution.
