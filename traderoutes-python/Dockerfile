# Reproducible development, test, and package-build environments for traderoutes.
# Build from this directory:
#   docker build --target dev   -t traderoutes-python-dev .
#   docker build --target test  -t traderoutes-python-test .
#   docker build --target build -t traderoutes-python-build .
#   docker build --target wheel-test -t traderoutes-python-wheel-test .

FROM python:3.13-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

# This file contains the pinned development/test toolchain and runtime
# dependencies used by the package tests.
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/requirements.txt

FROM base AS dev

COPY . .
ENV PYTHONPATH=/workspace/src

# Mount the source tree at /workspace for interactive development if desired.
CMD ["bash"]

FROM base AS test

COPY . .

# Install the package itself so tests exercise the installed package and its
# bundled graph assets rather than relying on PYTHONPATH.
RUN python -m pip install --no-cache-dir --no-build-isolation . \
    && python -m unittest discover -s tests -v

FROM base AS build

COPY . .

# The build target contains the wheel and source distribution under /dist.
RUN python -m pip install --no-cache-dir build \
    && python -m build --outdir /dist

FROM build AS wheel-test

# Test the exact wheel that would be uploaded to PyPI.
RUN python -m pip install --no-cache-dir /dist/*.whl \
    && python -m unittest discover -s tests -v

CMD ["bash"]
