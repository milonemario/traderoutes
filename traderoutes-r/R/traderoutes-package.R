#' traderoutes: Compute International Trade Routes
#'
#' Provides tools to query border relationships between countries and to compute
#' weighted shortest-path trade routes on a worldwide transportation network
#' combining roads, shipping lanes, and ports.
#'
#' Before installing or testing the package, make sure the GraphML files created
#' by the graph creation pipeline are present under `inst/extdata/`.
#'
#' @section Border functions:
#' [are_neighbors()], [get_neighbors()], [get_second_neighbors()],
#' [get_common_neighbors()]
#'
#' @section Route functions:
#' [countries()], [get_main_city()], [get_great_circle()], [get_path()],
#' [get_pattern()], [get_countries()], [road_distance()], [sea_distance()],
#' [transits_i()], [transits_j()]
#'
#' @docType package
#' @name traderoutes-package
#' @aliases traderoutes
"_PACKAGE"
