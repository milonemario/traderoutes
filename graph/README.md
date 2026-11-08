# Graph-generation pipeline

This directory contains the source data, graph-building code, and generated
artifacts used by the `traderoutes` Python and R packages.

The graph has already been generated for the current package release. You do
not need to rebuild it to install or test either package. The generated files
are kept under `FullGraph/` and the package-specific copies are kept in the
corresponding package directories.

## Inputs

The pipeline uses the following sources:

- Roads: [Natural Earth roads](https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_roads.zip).
- Country boundaries and country metadata: Natural Earth and project-provided
  country tables.
- Cities: a combination of CEPII country capitals and
  [SimpleMaps world cities](https://simplemaps.com/data/world-cities).
- Ports: World Port Source.
- Shipping network: the Oak Ridge National Laboratory CTA Transportation
  Network Group dataset, historically distributed through
  [GeoCommons](http://geocommons.com/datasets?id=25).

The source archives are tracked with Git LFS. Extracted copies of the Natural
Earth archives are not tracked; the graph code reads the ZIP archives directly.
Before working with the repository, retrieve the LFS objects:

```bash
git lfs pull
```

Check the licenses and attribution requirements of each upstream dataset
before redistributing derived data.

## Generated artifacts

The main outputs are:

```text
FullGraph/fullgraph.pkl       # Python full transportation graph
FullGraph/bordersgraph.pkl    # Python border graph
FullGraph/fullgraph.graphml   # R-compatible full transportation graph
FullGraph/bordersgraph.graphml# R-compatible border graph
```

The Python package contains pickle copies under
`../traderoutes-python/src/traderoutes/assets/`. The R package contains
GraphML copies under `../traderoutes-r/inst/extdata/`.

The generated files are large and are tracked with Git LFS where appropriate.
They must be present as real files, rather than LFS pointer files, when
building the package Docker images.

## Graph container

The [`Dockerfile`](Dockerfile) provides the graph-generation environment. It
installs the dependencies from [`requirements.txt`](requirements.txt) and
expects this directory to be mounted at `/data` when the container is run.

Build the image from the repository root with:

```bash
docker build -t traderoutes-graph ./graph
```

To open an interactive container without rebuilding the graph:

```bash
docker run --rm -it \
  -v "$PWD/graph:/data" \
  traderoutes-graph bash
```

The graph-generation script is `create_graph.py`. Run it only when you
intentionally want to regenerate the graph artifacts.
