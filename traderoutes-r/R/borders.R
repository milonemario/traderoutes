#' Check whether two countries share a land border
#'
#' @param country1 ISO 3-letter code of the first country (e.g. `"FRA"`).
#' @param country2 ISO 3-letter code of the second country (e.g. `"ITA"`).
#'
#' @return `TRUE` if the countries are direct neighbors, `FALSE` otherwise.
#'
#' @examples
#' \dontrun{
#' are_neighbors("FRA", "ITA")   # TRUE
#' are_neighbors("FRA", "USA")   # FALSE
#' }
#' @export
are_neighbors <- function(country1, country2) {
  country2 %in% get_neighbors(country1)
}


#' Return neighboring countries of a given country
#'
#' @param country ISO 3-letter code of the country (e.g. `"FRA"`).
#'
#' @return Character vector of ISO3 codes of countries sharing a land border
#'   with `country`. Returns `character(0)` if the country is not in the graph.
#'
#' @examples
#' \dontrun{
#' get_neighbors("USA")   # c("CAN", "MEX")
#' }
#' @export
get_neighbors <- function(country) {
  b  <- .b()
  vs <- igraph::V(b)
  names <- igraph::vertex_attr(b, "name")
  if (!(country %in% names)) return(character(0))
  idx  <- which(names == country)
  ns   <- igraph::neighbors(b, idx)
  igraph::vertex_attr(b, "name", ns)
}


#' Return countries reachable in exactly two border hops
#'
#' Returns countries that are two hops away from `country` in the border graph,
#' excluding `country` itself and its direct neighbors.
#'
#' @param country ISO 3-letter code of the country.
#'
#' @return Character vector of ISO3 codes of second-degree neighbors,
#'   in traversal order. Returns `character(0)` if the country is not found.
#'
#' @examples
#' \dontrun{
#' "PRT" %in% get_second_neighbors("FRA")   # TRUE
#' }
#' @export
get_second_neighbors <- function(country) {
  b         <- .b()
  names     <- igraph::vertex_attr(b, "name")
  if (!(country %in% names)) return(character(0))
  direct    <- get_neighbors(country)
  idx       <- which(names == country)
  ns        <- igraph::neighbors(b, idx)
  second    <- character(0)
  for (n in ns) {
    sns <- igraph::neighbors(b, n)
    sn_names <- igraph::vertex_attr(b, "name", sns)
    for (sn in sn_names) {
      if (!(sn %in% second) && !(sn %in% direct) && sn != country) {
        second <- c(second, sn)
      }
    }
  }
  second
}


#' Return countries that border both of two given countries
#'
#' @param country1 ISO 3-letter code of the first country.
#' @param country2 ISO 3-letter code of the second country.
#'
#' @return Character vector of ISO3 codes of countries neighboring both inputs.
#'   Returns `character(0)` if no common neighbors exist.
#'
#' @examples
#' \dontrun{
#' get_common_neighbors("FRA", "ITA")   # "CHE"
#' }
#' @export
get_common_neighbors <- function(country1, country2) {
  ns1 <- get_neighbors(country1)
  ns2 <- get_neighbors(country2)
  intersect(ns1, ns2)
}
