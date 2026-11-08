# Reproducible development, test, and package-build environments for
# traderoutes. Build from this directory:
#   podman build --target build-env -t traderoutes-r-build-env .
#   podman build --target test  -t traderoutes-r-test .
#   podman build --target build -t traderoutes-r-build .

FROM rocker/r2u:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        libxml2-dev \
        libglpk-dev \
        pkg-config \
        zip \
        r-cran-cpp11 \
        r-cran-testthat \
    && rm -rf /var/lib/apt/lists/*

# The Ubuntu igraph binary may omit GraphML support. Build R/igraph against
# libxml2 so read_graph(..., format = "graphml") works in the package tests.
RUN Rscript --vanilla -e "install.packages('igraph', repos='https://cloud.r-project.org', type='source', Ncpus=2)"

FROM base AS build-env

# Toolchain-only image. Mount the source tree and an output directory when
# building locally so artifacts are written directly to the host.
CMD ["/bin/bash"]

FROM base AS test

COPY . .

# Install the package and run its testthat suite against the package source.
RUN test -f inst/extdata/bordersgraph.graphml \
    && test -f inst/extdata/fullgraph.graphml \
    && R CMD INSTALL . \
    && Rscript --vanilla -e "library(traderoutes); stopifnot('FRA' %in% countries()); testthat::test_local('/workspace')"

CMD ["Rscript", "--vanilla", "-e", "library(traderoutes); stopifnot('FRA' %in% countries()); testthat::test_local('/workspace')"]

FROM build-env AS build

COPY . .

# Build the source package and run R's package checks. The resulting tarball
# is left in /workspace for extraction from the build container.
RUN R CMD build --no-manual --no-build-vignettes . \
    && R CMD check --no-manual --no-vignettes --no-build-vignettes traderoutes_*.tar.gz

CMD ["/bin/bash"]
