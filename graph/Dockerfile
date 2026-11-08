# Create the holdup_graph container to create the final graph

# Create image
# > podman build -t holdup_graph .
# > docker build -t holdup_graph .

# Create container
# > podman create -it --name holdup_graph -v ./:/data --privileged --user root holdup_graph
# > docker create -it --name holdup_graph -v ./:/data --privileged --user root holdup_graph

FROM python:3.13-slim-bookworm

COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

WORKDIR /data
