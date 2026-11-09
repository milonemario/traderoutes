# Package-private environment that holds the loaded graphs
.pkg_env <- new.env(parent = emptyenv())

.load_graph <- function(extdata, name, legacy_name) {
  rds_path <- file.path(extdata, paste0(name, ".rds"))
  graphml_path <- file.path(extdata, paste0(legacy_name, ".graphml"))

  if (file.exists(rds_path)) {
    return(readRDS(rds_path))
  }
  if (file.exists(graphml_path)) {
    return(igraph::read_graph(graphml_path, format = "graphml"))
  }
  NULL
}

.onLoad <- function(libname, pkgname) {
  extdata <- system.file("extdata", package = "traderoutes")

  .pkg_env$b <- .load_graph(extdata, "bordersgraph", "bordersgraph")
  .pkg_env$g <- .load_graph(extdata, "fullgraph", "fullgraph")

  if (is.null(.pkg_env$b)) {
    warning(
      "No borders graph found. Run tools/convert_graphml_to_rds.R before building.",
      call. = FALSE
    )
  }
  if (is.null(.pkg_env$g)) {
    warning(
      "No full graph found. Run tools/convert_graphml_to_rds.R before building.",
      call. = FALSE
    )
  }
}

# Internal helpers -----------------------------------------------------------

.b <- function() {
  if (is.null(.pkg_env$b))
    stop("Borders graph is not available. Generate bordersgraph.rds before installing the package.", call. = FALSE)
  .pkg_env$b
}

.g <- function() {
  if (is.null(.pkg_env$g))
    stop("Full graph is not available. Generate fullgraph.rds before installing the package.", call. = FALSE)
  .pkg_env$g
}
