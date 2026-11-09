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
  message(
    "  vertices=", igraph::vcount(graph),
    ", edges=", igraph::ecount(graph),
    ", vertex_attributes=", length(igraph::vertex_attr_names(graph)),
    ", edge_attributes=", length(igraph::edge_attr_names(graph))
  )

  message("Writing ", output)
  saveRDS(graph, output, compress = "xz")
  message("  size=", format(object.size(graph), units = "auto"),
          ", file_size=", format(file.info(output)$size, big.mark = ","), " bytes")
}

convert_one("bordersgraph")
convert_one("fullgraph")
