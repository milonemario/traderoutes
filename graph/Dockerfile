# Create the holdup_graph container to create the final graph

# Create image
# > podman build -t traderoutes-graph .

# Create container
# > podman create -it --name traderoutes-graph -v ./:/data --privileged --user root traderoutes-graph

FROM python:3.13-slim-bookworm

COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

WORKDIR /data
