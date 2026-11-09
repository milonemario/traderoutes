#!/usr/bin/env Rscript

usage <- function() {
  cat(
    "Usage: convert_graphml_to_rds.R",
    "--input-dir DIR --output-dir DIR\n",
    "\n",
    "Converts bordersgraph.graphml and fullgraph.graphml into compressed\n",
    "R-native igraph files for distribution with the traderoutes package.\n",
    sep = ""
  )
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 1L && args[[1L]] %in% c("-h", "--help")) {
  usage()
  quit(status = 0L)
}

read_option <- function(name) {
  i <- match(name, args)
  if (is.na(i) || i == length(args)) {
    stop(sprintf("Missing required option: %s", name), call. = FALSE)
  }
  args[[i + 1L]]
}

input_dir <- normalizePath(read_option("--input-dir"), mustWork = TRUE)
output_dir <- read_option("--output-dir")
if (!dir.exists(output_dir) && !dir.create(output_dir, recursive = TRUE)) {
  stop(sprintf("Could not create output directory: %s", output_dir), call. = FALSE)
}
output_dir <- normalizePath(output_dir, mustWork = TRUE)

if (!requireNamespace("igraph", quietly = TRUE)) {
  stop("The igraph package is required to run this conversion.", call. = FALSE)
}

convert_one <- function(name) {
  input <- file.path(input_dir, paste0(name, ".graphml"))
  output <- file.path(output_dir, paste0(name, ".rds"))

  if (!file.exists(input)) {
    stop(sprintf("Input graph does not exist: %s", input), call. = FALSE)
  }

  message("Reading ", input)
  graph <- igraph::read_graph(input, format = "graphml")

  # These attributes are present in the canonical graph but are not used by
  # the R package. Removing them reduces the distribution artifact while
  # leaving the source GraphML unchanged.
  unused_vertex_attributes <- c("capital", "landlocked", "connected")
  for (attribute in unused_vertex_attributes) {
    if (attribute %in% igraph::vertex_attr_names(graph)) {
      graph <- igraph::delete_vertex_attr(graph, attribute)
    }
  }

  message(
    "  vertices=", igraph::vcount(graph),
    ", edges=", igraph::ecount(graph),
    ", vertex_attributes=", length(igraph::vertex_attr_names(graph)),
    ", edge_attributes=", length(igraph::edge_attr_names(graph))
  )

  message("Writing ", output)
  # saveRDS() does not expose the XZ compression level directly. Writing to
  # an xz connection allows us to use the maximum level while keeping the
  # result readable by readRDS().
  connection <- xzfile(output, open = "wb", compression = 9)
  tryCatch(
    saveRDS(graph, connection, compress = FALSE),
    finally = close(connection)
  )
  message("  size=", format(object.size(graph), units = "auto"),
          ", file_size=", format(file.info(output)$size, big.mark = ","), " bytes")
}

convert_one("bordersgraph")
convert_one("fullgraph")
