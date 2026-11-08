# Package-private environment that holds the loaded graphs
.pkg_env <- new.env(parent = emptyenv())

.onLoad <- function(libname, pkgname) {
  extdata      <- system.file("extdata", package = "traderoutes")
  borders_path <- file.path(extdata, "bordersgraph.graphml")
  full_path    <- file.path(extdata, "fullgraph.graphml")

  if (file.exists(borders_path)) {
    .pkg_env$b <- igraph::read_graph(borders_path, format = "graphml")
  } else {
    warning(
      "bordersgraph.graphml not found in inst/extdata. ",
      "Copy bordersgraph.graphml into inst/extdata before installing the package.",
      call. = FALSE
    )
  }

  if (file.exists(full_path)) {
    .pkg_env$g <- igraph::read_graph(full_path, format = "graphml")
  } else {
    warning(
      "fullgraph.graphml not found in inst/extdata. ",
      "Copy fullgraph.graphml into inst/extdata before installing the package.",
      call. = FALSE
    )
  }
}

# Internal helpers -----------------------------------------------------------

.b <- function() {
  if (is.null(.pkg_env$b))
    stop("Borders graph not loaded. Copy bordersgraph.graphml into inst/extdata first.", call. = FALSE)
  .pkg_env$b
}

.g <- function() {
  if (is.null(.pkg_env$g))
    stop("Full graph not loaded. Copy fullgraph.graphml into inst/extdata first.", call. = FALSE)
  .pkg_env$g
}
